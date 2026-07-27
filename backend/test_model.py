"""Quick HPD model diagnostic — tests if model works on your GPU."""
import sys, os, time, torch

MODEL_DIR = os.path.join(os.path.dirname(__file__), "model")
sys.path.insert(0, MODEL_DIR)

print("1. Loading model...")
from transformers import AutoModel, AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, trust_remote_code=True, use_fast=False)
model = AutoModel.from_pretrained(
    MODEL_DIR, trust_remote_code=True,
    dtype=torch.bfloat16, attn_implementation="eager",
)

# Test on CPU first
print(f"2. PyTorch version: {torch.__version__}")
print(f"3. XPU available: {hasattr(torch, 'xpu') and torch.xpu.is_available()}")
print(f"4. CUDA available: {torch.cuda.is_available()}")

device = "cpu"
if hasattr(torch, 'xpu') and torch.xpu.is_available():
    device = "xpu"
    print("5a. Using Intel XPU")
elif torch.cuda.is_available():
    device = "cuda"
    print("5a. Using NVIDIA CUDA")
else:
    print("5a. Using CPU (slow)")

model = model.to(device)
model.eval()
model.load_mtp_weights()
print(f"6. Model on: {next(model.parameters()).device}")

# Test with a simple white image
print("\n7. Testing with simple image...")
from PIL import Image
img = Image.new("RGB", (448, 448), color="white")

from image_preprocess import (
    IMAGE_SIZE, MIN_DYNAMIC_PATCH, MAX_DYNAMIC_PATCH, USE_THUMBNAIL,
    get_target_ratios, dynamic_preprocess, build_transform,
)

min_num, max_num = MIN_DYNAMIC_PATCH, MAX_DYNAMIC_PATCH
if USE_THUMBNAIL and max_num != 1:
    max_num += 1
target_ratios = get_target_ratios(min_num, max_num)
transform = build_transform(IMAGE_SIZE)
tiles = dynamic_preprocess(img, target_ratios, IMAGE_SIZE, USE_THUMBNAIL)
pixel_values = torch.stack([transform(t) for t in tiles])
pixel_values = pixel_values.to(dtype=torch.bfloat16, device=device)
num_tiles = pixel_values.shape[0]
print(f"8. Tiles: {num_tiles}, Shape: {pixel_values.shape}, Device: {pixel_values.device}")

print("\n9. Running generate_hpd...")
t0 = time.time()
try:
    with torch.no_grad():
        result = model.generate_hpd(
            tokenizer=tokenizer,
            pixel_values=pixel_values,
            question="Parse this page.",
            generation_config={
                "max_new_tokens": 512, "do_sample": False,
                "num_beams": 1, "pad_token_id": tokenizer.pad_token_id,
            },
            use_mtp=True, num_speculative_tokens=6,
            num_patches_list=[num_tiles], verbose=True,
        )
    elapsed = time.time() - t0
    if result is None:
        print(f"\n❌ FAILED: Model returned None after {elapsed:.1f}s")
    else:
        print(f"\n✅ SUCCESS in {elapsed:.1f}s")
        print(f"Result length: {len(result)} chars")
        print(f"Preview: {result[:300]}...")
except Exception as e:
    print(f"\n❌ CRASHED after {time.time()-t0:.1f}s: {e}")
    import traceback
    traceback.print_exc()
