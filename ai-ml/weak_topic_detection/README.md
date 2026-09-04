# Weak Topic Detection

A module that analyzes quiz results to identify topics where a learner is performing weakly.

## Features

- Loads quiz results from JSON data
- Calculates accuracy for each topic
- Identifies weak topics using an accuracy threshold
- Requires a minimum number of attempts before evaluating a topic
- Provides a service and API interface
- Validates quiz-result data
- Includes automated tests

## Current Configuration

- Weak topic threshold: 60%
- Minimum attempts required: 3

## Project Structure

```text
weak_topic_detection/
├── app/
│   ├── api/
│   ├── detectors/
│   ├── models/
│   ├── services/
│   ├── utils/
│   ├── validators/
│   └── config.py
├── data/
│   └── quiz_results.json
└── tests/