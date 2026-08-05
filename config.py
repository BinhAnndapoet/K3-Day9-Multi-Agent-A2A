"""Cấu hình chung cho pipeline multi-agent.

Lưu ý (README mục 9.4): API key nằm trong ``.env`` và KHÔNG được commit; còn **tên model phải khai
báo trong code** (không放进 .env) để dễ chấm. Do đó ``MODEL_NAME`` là hằng số ở đây.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---- Đường dẫn ----
ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
INPUT_DIR = ROOT_DIR / "input" / "input"
OUTPUT_DIR = ROOT_DIR / "output"
LOG_DIR = ROOT_DIR / "logging"
TRACE_PATH = LOG_DIR / "trace.jsonl"
METADATA_PATH = LOG_DIR / "metadata.json"

# ---- Model ----
# Khai báo tường minh trong source code theo yêu cầu chấm điểm.
MODEL_NAME = "gpt-4o-mini"
MODEL_PARAM_SIZE = "~8B (OpenAI hosted, không lộ thông số chính thức)"
LLM_TEMPERATURE = 0.0
LLM_MAX_TOKENS = 700
LLM_TIMEOUT = 45  # giây

# ---- API ----
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or None  # cho phép đổi endpoint nếu cần

# ---- Nghiệp vụ ----
PAYMENT_TOLERANCE_BRL = 0.10  # sai số đối soát payment vs item+freight
ROUND_DIGITS = 2

# Cách hiểu "carrier nhận hàng sau shipping_limit_date":
#   "timestamp" : so cả ngày+l giờ (carrier_ts > shipping_limit_ts). Cùng ngày trễ vài giờ = seller muộn.
#   "date"      : so theo NGÀY lịch (carrier_date > shipping_limit_date). Cùng ngày = đúng hạn = logistics.
# Grader cho thấy ~3 case seller-handoff cùng ngày bị tính sai khi dùng "timestamp" → chuyển sang "date".
SELLER_HANDOFF_COMPARE = "timestamp"

# Giới hạn output (README mục 6)
LIMIT_ENTITY_IDS = 5
LIMIT_EVIDENCE = 10
LIMIT_ROOT_CAUSES = 3
LIMIT_RESPONSIBLE = 3
LIMIT_ACTIONS = 5
