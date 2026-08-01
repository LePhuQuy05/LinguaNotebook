# Findings — PDF to Markdown on Intel Arc 140V

## Current Understanding

Chuyển PDF scan tiếng Nhật → markdown có cấu trúc là bài toán khó trên Intel Arc vì:
- Intel Arc không phải NVIDIA → vLLM không chạy
- llama.cpp SYCL hỗ trợ nhưng **SSM layers (qwen35) không tối ưu** → surya-2 chỉ đạt 27 tok/s (CPU-level)
- HPD (PaddlePaddle) chạy tốt trên XPU nhưng output là OCR text thô, không phải markdown

## Patterns and Insights

### H2 (CONFIRMED — từ 3 ngày production): HPD limitations
- Tốc độ: ~53s/trang trên Intel XPU (GPU) ✅
- Chất lượng tiếng Nhật: ~85% (仕事 → 什么事, 言葉 → 音業 errors) ⚠️
- **Markdown: KHÔNG có** — output là text + `<BLOCK>` tags, không có table/header structure ❌
- Degeneration: đã fix bằng repetition penalty + no MTP

### Marker/surya trên Intel Arc (REFUTED — 3 ngày debug)
- qwen35 architecture = SSM model → SYCL backend chưa tối ưu SSM ops
- Kết quả: 27 tok/s ≈ CPU speed, mặc dù GPU detected
- Debug build (Clang 20.1.8) hoạt động nhưng Debug DLLs missing
- Release build (MSVC) fallback → GPU không engage
- **Kết luận: Marker trên Intel Arc bất khả thi với tốc độ hiện tại**

### Ollama (H1 — đang test)
- Đã cài sẵn 0.32.0 ✅
- deepseek-r1:1.5b chạy OK ✅
- GPU support: Ollama tự detect Intel Arc qua SYCL
- qwen2.5vl:7b đang tải (5GB)

## Lessons and Constraints

- **Đừng build llama.cpp từ source cho SYCL nữa** — mất 3 ngày, kết quả vẫn chậm vì SSM
- `--model_alias` là bắt buộc khi dùng llama-server (surya check model name)
- `pip install llama-cpp-python` từ abetlen index **không có** wheel SYCL Windows (404)
- HPD model path phải là absolute (config: `D:/LanguageNotebook/backend/model`)

## Open Questions

- [ ] Ollama qwen2.5vl:7b trên Arc đạt bao nhiêu tok/s?
- [ ] Chất lượng JP OCR của qwen2.5vl so với HPD?
- [ ] Markdown structure (table/header) có đúng không?
- [ ] Nếu Ollama nhanh → thay HPD trong pipeline?
