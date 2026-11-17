from app.parsers.instagram_parser import normalize_instagram_text


def test_normalize_instagram_text_recovers_valid_text_before_truncated_suffix():
    mojibake = (
        "Ð\u009dÐ\u0095Ð¢Ð\u0098Ð\u009fÐ\u0098Ð§Ð\u009dÐ«Ð\u0098Ì\u0086 "
        "Ð\u009fÐ\u0098Ð¢Ð\u0095Ð"
    )

    assert normalize_instagram_text(mojibake) == (
        "\u041d\u0415\u0422\u0418\u041f\u0418\u0427\u041d\u042b\u0418\u0306 "
        "\u041f\u0418\u0422\u0415"
    )


def test_normalize_instagram_text_handles_truncated_suffix_before_whitespace():
    mojibake = (
        "Ð\u009dÐ\u0095Ð¢Ð\u0098Ð\u009fÐ\u0098Ð§Ð\u009dÐ«Ð\u0098Ì\u0086 "
        "Ð\u009fÐ\u0098Ð¢Ð\u0095Ð "
    )

    assert normalize_instagram_text(mojibake) == (
        "\u041d\u0415\u0422\u0418\u041f\u0418\u0427\u041d\u042b\u0418\u0306 "
        "\u041f\u0418\u0422\u0415 "
    )


def test_normalize_instagram_text_keeps_other_invalid_sequences_unchanged():
    mojibake = "Ð!Ð\u0095"

    assert normalize_instagram_text(mojibake) == mojibake
