def predict_plant_condition(image_path: str) -> dict:
    """
    Temporary AI prediction service.

    Later, this function will load the trained basil disease model
    and return the real predicted condition and confidence.
    """

    return {
        "condition": "Healthy",
        "confidence": 0.90
    }