from app.models.resume import Resume


def test_resume_model_columns_do_not_use_native_enums():
    assert Resume.__table__.c.parse_status.type.length == 32
    assert Resume.__table__.c.file_sha256.type.length == 64
    assert Resume.__table__.c.storage_path.type.python_type is str
