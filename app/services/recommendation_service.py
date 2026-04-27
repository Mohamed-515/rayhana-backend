def generate_recommendation(condition: str) -> str:
    recommendations = {
        "Healthy": (
            "The plant appears healthy. Continue regular watering, provide enough sunlight, "
            "and monitor the leaves for any color changes or spots."
        ),
        "Fungal Disease": (
            "The plant may show signs of fungal disease. Remove affected leaves, avoid watering "
            "the leaves directly, improve air circulation, and monitor the plant closely."
        ),
        "Downy Mildew": (
            "The plant may be affected by downy mildew. Reduce leaf moisture, improve ventilation, "
            "avoid overcrowding, and remove infected leaves to limit spreading."
        ),
        "Fusarium Wilt": (
            "The plant may show signs of fusarium wilt. Isolate the affected plant, avoid overwatering, "
            "check soil drainage, and consider replacing contaminated soil if the condition worsens."
        ),
        "Unknown": (
            "The plant condition could not be identified clearly. Upload a clearer image with good lighting "
            "and make sure the leaves are visible."
        )
    }

    return recommendations.get(condition, recommendations["Unknown"])