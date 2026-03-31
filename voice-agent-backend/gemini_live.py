"""
session.py — Quản lý một phiên hội thoại khám bệnh với Gemini Live API.

Luồng hoạt động tổng thể:
  Trình duyệt (micro) → Task1 → audio_out_queue → Task2 → Gemini Live API
  Gemini Live API → Task3 → audio_in_queue → Task4 → Trình duyệt (loa + UI)

Khi AI báo hiệu complete_intake(), Task4 sẽ gọi extractor để tạo phiếu khám JSON
rồi lưu vào EMR thông qua emr_service.
"""

import asyncio
import inspect
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import live as live_module
from google.genai import types

from config import settings
from services.emr_service import EMRService  # Kết nối EMR

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Patch tương thích websockets
# ---------------------------------------------------------------------------


def _patch_websockets_for_headers() -> None:
    """
    [Bước 0 — Khởi động] Vá hàm ws_connect của thư viện google-genai.

    Thư viện google-genai gọi ws_connect() với tham số `additional_headers`,
    nhưng một số phiên bản websockets cũ không nhận tham số đó — gây lỗi
    ngay khi kết nối. Hàm này kiểm tra và thêm wrapper để chuyển
    `additional_headers` thành `extra_headers` nếu cần.

    Chỉ chạy một lần khi import module.
    """
    target = getattr(live_module, "ws_connect", None)
    if target is None:
        return

    try:
        sig = inspect.signature(target)
    except (TypeError, ValueError):
        return

    if "additional_headers" in sig.parameters:
        return

    def connect_wrapper(*args, additional_headers=None, **kwargs):
        if additional_headers is not None and "extra_headers" not in kwargs:
            kwargs["extra_headers"] = additional_headers
        return target(*args, **kwargs)

    live_module.ws_connect = connect_wrapper


_patch_websockets_for_headers()


# ---------------------------------------------------------------------------
# Hằng số cấu hình (lấy từ settings / .env)
# ---------------------------------------------------------------------------

FORMAT = settings.AUDIO_FORMAT
CHANNELS = settings.AUDIO_CHANNELS
SEND_SAMPLE_RATE = settings.SEND_SAMPLE_RATE
RECEIVE_SAMPLE_RATE = settings.RECEIVE_SAMPLE_RATE
MODEL = settings.MODEL_NAME


# ---------------------------------------------------------------------------
# Lớp chính
# ---------------------------------------------------------------------------


class GeminiLiveSession:
    """
    Quản lý toàn bộ vòng đời của một phiên khám bệnh.

    Mỗi phiên gồm 4 task chạy song song:
      Task 1 — Nhận audio/lệnh từ trình duyệt → đẩy vào audio_out_queue
      Task 2 — Lấy từ audio_out_queue → gửi lên Gemini
      Task 3 — Nhận phản hồi từ Gemini → đẩy vào audio_in_queue
      Task 4 — Lấy từ audio_in_queue → gửi về trình duyệt / xử lý sự kiện

    Khi AI gọi complete_intake():
      → _generate_structured_data() trích xuất phiếu khám JSON
      → emr_service.save_intake() lưu vào EMR
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = genai.Client(
            http_options={"api_version": "v1beta"},
            api_key=api_key,
        )

        self.audio_in_queue: asyncio.Queue = None
        self.audio_out_queue: asyncio.Queue = None

        self.session = None
        self.websocket = None

        self.conversation_history: List[Dict[str, str]] = []

        self._current_assistant_text = ""
        self._current_patient_text = ""
        self.current_step = 0

        self.latest_structured: Optional[Dict[str, Any]] = None

        self.session_id = str(uuid.uuid4())
        self.session_log_file: Optional[str] = None

    # -----------------------------------------------------------------------
    # ĐIỀU PHỐI CHÍNH
    # -----------------------------------------------------------------------

    async def run(self, websocket) -> None:
        """
        [Bước 1 — Khởi động phiên] Kết nối Gemini và chạy 4 task song song.
        """
        self.websocket = websocket

        if settings.ENABLE_SESSION_LOGS:
            self._init_session_log()

        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=settings.VOICE_MODEL
                    )
                )
            ),
            system_instruction=types.Content(
                parts=[types.Part(text=self._build_system_prompt())]
            ),
            generation_config=types.GenerationConfig(
                temperature=0.2,
                top_p=0.95,
            ),
            tools=[
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name="complete_intake",
                            description=(
                                "Gọi hàm này khi đã thu thập ĐỦ thông tin y tế theo 7 bước "
                                "và bệnh nhân đã xác nhận bản tóm tắt."
                            ),
                        ),
                        types.FunctionDeclaration(
                            name="report_step",
                            description=(
                                "Báo cáo bước hiện tại đang thực hiện trong lộ trình 7 bước. "
                                "Phải gọi hàm này ngay khi bắt đầu một bước mới hoặc chuyển bước."
                            ),
                            parameters=types.Schema(
                                type="OBJECT",
                                properties={
                                    "step_index": types.Schema(
                                        type="INTEGER",
                                        description="Số thứ tự bước (1-7)",
                                    ),
                                    "step_name": types.Schema(
                                        type="STRING",
                                        description="Tên bước hiện tại",
                                    ),
                                },
                                required=["step_index", "step_name"],
                            ),
                        ),
                    ]
                )
            ],
        )

        logger.info("Đang kết nối Gemini Live API...")

        try:
            async with self.client.aio.live.connect(
                model=MODEL, config=config
            ) as session:
                self.session = session

                self.audio_in_queue = asyncio.Queue()
                self.audio_out_queue = asyncio.Queue(maxsize=5)

                await websocket.send_json(
                    {
                        "type": "status",
                        "state": "ready",
                        "message": "Đã kết nối Gemini",
                    }
                )

                tasks = [
                    asyncio.create_task(self._task1_receive_from_frontend()),
                    asyncio.create_task(self._task2_send_to_gemini()),
                    asyncio.create_task(self._task3_receive_from_gemini()),
                    asyncio.create_task(self._task4_send_to_frontend()),
                ]
                await asyncio.gather(*tasks, return_exceptions=True)

        except asyncio.CancelledError:
            logger.info("Phiên bị huỷ")
        except Exception as e:
            logger.error(f"Lỗi phiên: {e}", exc_info=True)
            try:
                await websocket.send_json({"type": "error", "message": str(e)})
            except Exception:
                pass

    # -----------------------------------------------------------------------
    # TASK 1 — Nhận từ trình duyệt
    # -----------------------------------------------------------------------

    async def _task1_receive_from_frontend(self) -> None:
        """
        [Task 1] Lắng nghe WebSocket, phân loại và xử lý.

          - bytes : Chunk âm thanh từ micro → audio_out_queue
          - text  : Lệnh JSON (interrupt / chat_text / end_session)
        """
        logger.info("Task 1 bắt đầu: nhận từ trình duyệt")
        try:
            while True:
                message = await self.websocket.receive()

                if "bytes" in message:
                    await self.audio_out_queue.put(
                        {"data": message["bytes"], "mime_type": "audio/pcm"}
                    )

                elif "text" in message:
                    data = json.loads(message["text"])
                    if data.get("type") == "interrupt":
                        await self._flush_audio_queue()
                    elif data.get("type") == "chat_text":
                        text = data.get("text")
                        if text:
                            logger.info(f"DEBUG Chat: {text}")
                            await self.session.send(input=text, end_of_turn=True)
                    elif data.get("type") == "end_session":
                        raise asyncio.CancelledError("Người dùng kết thúc phiên")

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Task 1 lỗi: {e}")
            raise

    # -----------------------------------------------------------------------
    # TASK 2 — Gửi lên Gemini
    # -----------------------------------------------------------------------

    async def _task2_send_to_gemini(self) -> None:
        """
        [Task 2] Lấy chunk từ audio_out_queue và gửi lên Gemini.
        """
        logger.info("Task 2 bắt đầu: gửi lên Gemini")
        try:
            while True:
                audio_data = await self.audio_out_queue.get()
                await self.session.send(input=audio_data)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Task 2 lỗi: {e}")
            raise

    # -----------------------------------------------------------------------
    # TASK 3 — Nhận từ Gemini
    # -----------------------------------------------------------------------

    async def _task3_receive_from_gemini(self) -> None:
        """
        [Task 3] Nhận và phân loại tất cả sự kiện từ Gemini:

          1. input_transcription  → gom _current_patient_text
          2. response.data        → chunk âm thanh AI
          3. output_transcription → gom _current_assistant_text (nguồn CHÍNH)
          4. tool_call            → complete_intake / report_step
          5. turn_complete        → chốt lượt, đẩy sự kiện
        """
        logger.info("Task 3 bắt đầu: nhận từ Gemini")
        try:
            while True:
                async for response in self.session.receive():

                    server = getattr(response, "server_content", None)

                    # 1. Transcript bệnh nhân
                    if server:
                        input_trans = getattr(server, "input_transcription", None)
                        if input_trans:
                            text = getattr(input_trans, "text", "")
                            if text:
                                self._current_patient_text += text
                                await self.audio_in_queue.put(
                                    {
                                        "type": "transcript",
                                        "role": "patient",
                                        "text": text,
                                    }
                                )

                    # 2. Chunk âm thanh AI
                    if response.data:
                        await self.audio_in_queue.put(
                            {"type": "audio", "data": response.data}
                        )

                    # 3. Transcript AI (nguồn CHÍNH trong AUDIO mode)
                    if server:
                        output_trans = getattr(server, "output_transcription", None)
                        if output_trans:
                            text = getattr(output_trans, "text", "")
                            if text:
                                self._current_assistant_text += text
                                await self.audio_in_queue.put(
                                    {
                                        "type": "transcript",
                                        "role": "assistant",
                                        "text": text,
                                    }
                                )

                    # 4. Tool call
                    if response.tool_call and response.tool_call.function_calls:
                        for func_call in response.tool_call.function_calls:
                            if func_call.name == "complete_intake":
                                self._log_event(
                                    "function_call", data={"name": "complete_intake"}
                                )
                                await self.audio_in_queue.put(
                                    {
                                        "type": "function_call",
                                        "function_name": "complete_intake",
                                    }
                                )
                            elif func_call.name == "report_step":
                                step_idx = func_call.args.get("step_index")
                                step_name = func_call.args.get("step_name")
                                self.current_step = step_idx
                                logger.info(
                                    f"[INTERNAL STATE] Chuyển tới Bước {step_idx}: {step_name}"
                                )
                                self._log_event("report_step", data=func_call.args)

                    # 5. Kết thúc lượt
                    if server and getattr(server, "turn_complete", False):
                        self._finalize_turn()
                        await self.audio_in_queue.put({"type": "turn_complete"})

        except asyncio.CancelledError:
            logger.info("Task 3 dừng")
            raise
        except Exception as e:
            logger.error(f"Task 3 lỗi: {e}", exc_info=True)
            raise

    # -----------------------------------------------------------------------
    # TASK 4 — Gửi về trình duyệt và xử lý sự kiện
    # -----------------------------------------------------------------------

    async def _task4_send_to_frontend(self) -> None:
        """
        [Task 4] Lấy sự kiện từ audio_in_queue và xử lý:

          "audio"         → gửi binary tới trình duyệt
          "transcript"    → gửi JSON hiển thị chữ
          "function_call" → trích xuất phiếu khám → lưu EMR → thông báo hoàn thành
          "turn_complete" → báo trình duyệt cập nhật UI
        """
        logger.info("Task 4 bắt đầu: gửi về trình duyệt")
        try:
            while True:
                event = await self.audio_in_queue.get()
                event_type = event["type"]

                if event_type == "audio":
                    await self.websocket.send_bytes(event["data"])

                elif event_type == "transcript":
                    await self.websocket.send_json(
                        {
                            "type": "transcript",
                            "role": event["role"],
                            "text": event["text"],
                        }
                    )

                elif (
                    event_type == "function_call"
                    and event.get("function_name") == "complete_intake"
                ):
                    logger.info("Nhận complete_intake — đang trích xuất phiếu khám...")

                    structured = await self._generate_structured_data()

                    if structured:
                        # Lưu vào EMR — nguồn lưu trữ duy nhất
                        emr_result = await EMRService.save_intake(structured)
                        logger.info(
                            f"Đã lưu EMR: record_id={emr_result.get('record_id')}"
                        )

                        await self.websocket.send_json(
                            {
                                "type": "extracted_data",
                                "data": structured,
                                "emr_record_id": emr_result.get("record_id"),
                            }
                        )

                    await self.websocket.send_json(
                        {
                            "type": "intake_complete",
                            "message": "Phiếu khám đã hoàn thành",
                        }
                    )

                elif event_type == "turn_complete":
                    await self.websocket.send_json({"type": "turn_complete"})

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Task 4 lỗi: {e}", exc_info=True)
            raise

    # -----------------------------------------------------------------------
    # XỬ LÝ NỘI BỘ
    # -----------------------------------------------------------------------

    async def _flush_audio_queue(self) -> None:
        """Xoá toàn bộ audio_in_queue để dừng phát khi bệnh nhân ngắt."""
        while not self.audio_in_queue.empty():
            try:
                self.audio_in_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    def _finalize_turn(self) -> None:
        """
        Chốt và lưu text đã gom trong lượt vào conversation_history.
        Giới hạn tối đa 40 lượt để tránh quá dài.
        """
        if self._current_assistant_text.strip():
            self.conversation_history.append(
                {"role": "assistant", "text": self._current_assistant_text.strip()}
            )
            logger.debug(f"Lưu lượt AI: {self._current_assistant_text[:80]}...")
        self._current_assistant_text = ""

        if self._current_patient_text.strip():
            self.conversation_history.append(
                {"role": "user", "text": self._current_patient_text.strip()}
            )
            logger.debug(f"Lưu lượt bệnh nhân: {self._current_patient_text[:80]}...")
        self._current_patient_text = ""

        if len(self.conversation_history) > 40:
            self.conversation_history = self.conversation_history[-40:]

    # -----------------------------------------------------------------------
    # TRÍCH XUẤT PHIẾU KHÁM
    # -----------------------------------------------------------------------

    async def _generate_structured_data(self) -> Optional[Dict[str, Any]]:
        """
        Gọi Gemini lần 2 để trích xuất phiếu khám JSON từ conversation_history.

        Trả về Dict phiếu khám, hoặc latest_structured nếu thất bại.
        """
        logger.info(
            "Bắt đầu trích xuất phiếu khám từ %d lượt hội thoại",
            len(self.conversation_history),
        )

        if len(self.conversation_history) < 2:
            logger.warning("Chưa đủ dữ liệu để trích xuất")
            return self.latest_structured

        transcript = "\n".join(
            f"{turn['role'].capitalize()}: {turn['text']}"
            for turn in self.conversation_history
        )

        prompt = (
            "Bạn là chuyên gia trích xuất dữ liệu y tế. Dựa trên hội thoại, hãy trả về JSON khớp hoàn toàn với cấu trúc sau:\n"
            "{\n"
            '  "patient_info": {"name": str, "date_of_birth": str, "gender": str, "phone": str, "email": str, "address": str},\n'
            '  "present_illness": {\n'
            '    "chief_complaints": [{"complaint": str, "onset": str, "duration": str, "severity": str, "Location": str}],\n'
            '    "symptoms": [str],\n'
            '    "timeline": str\n'
            "  },\n"
            '  "medications": [{"name": str, "dose": str, "frequency": str, "route": str, "indication": str, "adherence": str, "effectiveness": str}],\n'
            '  "allergies": [{"allergen": str, "reaction": str, "severity": str, "requires_intervention": bool}],\n'
            '  "past_medical_history": {"conditions": [str], "surgeries": [str], "hospitalizations": [str]},\n'
            '  "family_history": {"conditions": [str]},\n'
            '  "social_history": {"smoking": str, "alcohol": str, "drugs": str, "occupation": str, "exercise": str}\n'
            "}\n"
            "Lưu ý: Chỉ trả về JSON, không thêm văn bản khác. Nếu thông tin nào không có, hãy để null hoặc mảng rỗng [].\n\n"
            f"Hội thoại:\n{transcript}"
        )

        try:
            response = await self.client.aio.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            self.latest_structured = json.loads(response.text)
            logger.info("Trích xuất phiếu khám thành công")
            return self.latest_structured

        except Exception as e:
            logger.error(f"Trích xuất phiếu khám thất bại: {e}", exc_info=True)
            return self.latest_structured

    # -----------------------------------------------------------------------
    # SYSTEM PROMPT
    # -----------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        """Tạo system prompt định nghĩa vai trò và quy trình 7 bước cho AI."""
        clinic = settings.CLINIC_NAME
        specialty = settings.SPECIALTY

        return f"""Bạn là trợ lý y tế của {clinic} ({specialty}).

Nhiệm vụ: Thu thập đủ thông tin bệnh án qua 7 bước theo thứ tự.

═══════════════════════════════════════

CẤU TRÚC 7 BƯỚC — BẮT BUỘC THEO THỨ TỰ

═══════════════════════════════════════

BƯỚC 1 — THÔNG TIN CÁ NHÂN

  Thu thập: Họ tên | Ngày sinh | Giới tính | Số điện thoại

  Chuyển bước khi: Có đủ 4 thông tin trên.

BƯỚC 2 — TRIỆU CHỨNG CHÍNH

  Thu thập: Triệu chứng là gì | Vị trí cụ thể | Khởi phát khi nào | Mức độ (thang 1-10) | Yếu tố làm nặng/nhẹ hơn

  Chuyển bước khi: Biết rõ triệu chứng, vị trí, thời gian, mức độ.

BƯỚC 3 — THUỐC ĐANG DÙNG

  Thu thập: Tên thuốc | Liều dùng | Tần suất | Lý do dùng

  Nếu bệnh nhân nói "có uống thuốc" → hỏi tiếp tên thuốc, liều, tần suất.

  Nếu bệnh nhân nói "không dùng thuốc" → xác nhận lại "Kể cả thuốc không kê đơn như vitamin, thuốc giảm đau?" → nếu xác nhận không → chuyển bước.

  Chuyển bước khi: Đã liệt kê hết thuốc HOẶC xác nhận không dùng gì.

BƯỚC 4 — DỊ ỨNG

  Thu thập: Chất gây dị ứng | Phản ứng cụ thể | Mức độ nghiêm trọng

  Nếu bệnh nhân nói "có dị ứng" → hỏi tiếp: dị ứng với gì, phản ứng ra sao.

  Nếu bệnh nhân nói "không" → xác nhận "Không dị ứng thuốc, thức ăn hay bất kỳ thứ gì?" → chuyển bước.

  Chuyển bước khi: Đã ghi nhận đầy đủ HOẶC xác nhận không có dị ứng.

BƯỚC 5 — TIỀN SỬ BẢN THÂN

  Thu thập: Bệnh mãn tính đang có | Phẫu thuật đã qua | Lần nhập viện gần nhất

  Nếu bệnh nhân nói "có bệnh nền" → hỏi bệnh gì, đang điều trị ở đâu.

  Chuyển bước khi: Đã hỏi đủ 3 mục hoặc bệnh nhân xác nhận không có.

BƯỚC 6 — TIỀN SỬ GIA ĐÌNH

  Thu thập: Bố/mẹ/anh chị em có bệnh di truyền hay bệnh lý gì không

  Chuyển bước khi: Có câu trả lời rõ ràng.

BƯỚC 7 — THÓI QUEN SINH HOẠT

  Thu thập: Hút thuốc | Rượu bia | Nghề nghiệp | Tập thể dục

  Chuyển bước khi: Đã hỏi đủ 4 mục.

═══════════════════════════════════════

QUY TẮC XỬ LÝ TRONG MỖI BƯỚC

═══════════════════════════════════════

HỎI TỪNG CÂU MỘT:

  - Mỗi lần chỉ hỏi 1 câu. Đợi trả lời xong mới hỏi tiếp.

  - Hỏi các câu con trong bước cho đến khi đủ thông tin → mới chuyển bước.

LÀM RÕ KHI MƠ HỒ:

  - Câu trả lời mơ hồ → hỏi lại câu con ngay, không bỏ qua.

  - Câu trả lời quá ngắn (ừ, không, có) → hỏi thêm chi tiết.

BÁM BỘ KHI LẠC ĐỀ:

  - Bệnh nhân hỏi ngoài lề → trả lời ngắn gọn lịch sự → nhắc lại đúng câu hỏi đang dở.

  - Không được bỏ qua câu hỏi chưa có đủ thông tin.

  - Ví dụ: "Cảm ơn bạn đã chia sẻ. Quay lại câu hỏi lúc nãy — [lặp lại câu hỏi]."

KHÔNG TỰ SUY DIỄN:

  - Chỉ ghi nhận những gì bệnh nhân nói thật sự.

  - Không tự điền "bình thường", "không có" khi chưa hỏi.

═══════════════════════════════════════

KẾT THÚC PHIÊN

═══════════════════════════════════════

Sau khi xong bước 7:

  1. Đọc lại toàn bộ thông tin đã thu thập.

  2. Hỏi: "Tôi tóm tắt như vậy đã đúng chưa?"

  3. Bệnh nhân xác nhận → gọi complete_intake().

  Không gọi complete_intake() trước bước này.

"""

    # -----------------------------------------------------------------------
    # LOGGING
    # -----------------------------------------------------------------------

    def _init_session_log(self) -> None:
        """Khởi tạo file log JSONL cho phiên hiện tại."""
        import os

        os.makedirs(settings.SESSION_LOG_PATH, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"session_{timestamp}_{self.session_id[:8]}.jsonl"
        self.session_log_file = os.path.join(settings.SESSION_LOG_PATH, filename)

        with open(self.session_log_file, "w", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "event": "session_start",
                        "session_id": self.session_id,
                        "timestamp": datetime.now().isoformat(),
                        "clinic": settings.CLINIC_NAME,
                        "voice_model": settings.VOICE_MODEL,
                    }
                )
                + "\n"
            )

        logger.info(f"File log phiên: {self.session_log_file}")

    def _log_event(
        self, event_type: str, data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Ghi một sự kiện vào file log JSONL."""
        if not self.session_log_file:
            return

        try:
            event = {
                "event": event_type,
                "timestamp": datetime.now().isoformat(),
                "data": data or {},
            }
            with open(self.session_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Không thể ghi log sự kiện: {e}")

    # -----------------------------------------------------------------------
    # DỌN DẸP
    # -----------------------------------------------------------------------

    async def cleanup(self) -> None:
        """Giải phóng tài nguyên khi phiên kết thúc."""
        logger.info(f"Dọn dẹp phiên {self.session_id[:8]}")
        self.session = None
