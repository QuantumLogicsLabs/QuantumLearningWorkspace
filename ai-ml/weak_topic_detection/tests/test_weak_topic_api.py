from app.api.weak_topic_api import WeakTopicAPI


def test_get_weak_topics():
    api = WeakTopicAPI()

    result = api.get_weak_topics()

    assert isinstance(result, list)
    assert len(result) > 0

    for topic in result:
        assert "topic" in topic
        assert "accuracy" in topic
        assert "attempts" in topic