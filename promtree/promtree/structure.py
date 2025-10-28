import os
import json
from collections import defaultdict
from PIL import Image
from surya.foundation import FoundationPredictor
from surya.layout import LayoutPredictor
from surya.debug.draw import draw_polys_on_image
from surya.settings import settings
import copy

def detect_layout(img_dir: str, output_dir: str) -> None:
    """
    Detect layout elements in images using Surya layout detection model.

    Args:
        img_dir (str): 이미지들이 저장된 디렉토리 경로
        output_dir (str): 레이아웃 분석 결과를 저장할 디렉토리 경로
    """

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Load images from directory
    images = []
    image_names = []
    for img_file in sorted(os.listdir(img_dir)):
        if img_file.lower().endswith(('.png', '.jpg', '.jpeg')):
            img_path = os.path.join(img_dir, img_file)
            images.append(Image.open(img_path))
            image_names.append(os.path.splitext(img_file)[0])

    if not images:
        print(f"No images found in {img_dir}")
        return

    # Initialize Surya models
    foundation_predictor = FoundationPredictor(checkpoint=settings.LAYOUT_MODEL_CHECKPOINT)
    layout_predictor = LayoutPredictor(foundation_predictor)

    # Run layout detection
    layout_predictions = layout_predictor(images)

    # Save annotated images with bounding boxes
    for idx, (image, layout_pred, name) in enumerate(
        zip(images, layout_predictions, image_names)
    ):
        polygons = [p.polygon for p in layout_pred.bboxes]
        labels = [f"{p.label}-{p.position}" for p in layout_pred.bboxes]
        bbox_image = draw_polys_on_image(
            polygons, copy.deepcopy(image), labels=labels
        )
        bbox_image.save(
            os.path.join(output_dir, f"{name}_{idx}_layout.png")
        )

    # Save results to JSON
    predictions_by_page = defaultdict(list)
    for idx, (pred, name, image) in enumerate(
        zip(layout_predictions, image_names, images)
    ):
        out_pred = pred.model_dump()
        out_pred["page"] = len(predictions_by_page[name]) + 1
        predictions_by_page[name].append(out_pred)

    with open(
        os.path.join(output_dir, "results.json"), "w+", encoding="utf-8"
    ) as f:
        json.dump(predictions_by_page, f, ensure_ascii=False, indent=2)

    print(f"Layout detection complete. Results saved to {output_dir}")
