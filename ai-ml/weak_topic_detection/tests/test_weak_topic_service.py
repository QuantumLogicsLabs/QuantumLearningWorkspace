from app.services.weak_topic_service import WeakTopicService


def main():
    service = WeakTopicService()

    weak_topics = service.get_weak_topics()

    print("\n========== Weak Topic Detection Output ==========\n")

    if not weak_topics:
        print("No weak topics detected.")
        return

    for index, topic in enumerate(weak_topics, start=1):
        print(
            f"{index}. {topic['topic']} - "
            f"Accuracy: {topic['accuracy']}% - "
            f"Attempts: {topic['attempts']}"
        )


if __name__ == "__main__":
    main()