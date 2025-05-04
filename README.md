# PurePost

![Django](https://img.shields.io/badge/Django-5.x-092E20?logo=django&logoColor=white) ![Django REST Framework](https://img.shields.io/badge/DRF-REST%20API-ff1709?logo=django&logoColor=white) ![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white) ![MinIO](https://img.shields.io/badge/MinIO-FF4C2B?logo=minio&logoColor=white) ![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?logo=pytorch&logoColor=white) ![ONNX](https://img.shields.io/badge/ONNX-005CED?logo=onnx&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)

![PurePost Logo](./docs/307icon200.jpeg)

**PurePost** is an innovative social media platform designed to provide users with a safe and trustworthy content-sharing experience. By integrating deepfake detection tools, PurePost helps users identify potentially fake content, ensuring the authenticity of shared information.

---

## Code Repository

The frontend repository is responsible for managing the UI layout and design, optimized for mobile devices.
[PurePost Frontend Repository](https://github.com/01-LinYi/PurePost-frontend)

The backend repository handles user management, content posting, social interactions, and deepfake detection:  
[PurePost Backend Repository](https://github.com/01-LinYi/PurePost-backend)

---

## Features

- **User Management**: Registration, login, and profile management.
- **Content Publishing**: Post text & images with tags and location markers.
- **Deepfake Detection**: Detect and flag potentially fake content.
- **Social Interactions**: Follow, like, comment, save(bookmark), and send private messages.
- **Content Recommendations[TODO]**: Personalized recommendations based on user behavior.
- **Notification System**: Real-time notifications for interactions and content moderation status.
- **I18N[TODO]**: Support for multiple languages and translation tools.

---

## Tech Stack

- **Frontend**: React Native (TypeScript), Expo ([CNG](https://docs.expo.dev/workflow/continuous-native-generation/) workflow, supports native builds and Expo Go)
- **Backend**: Django (Python, with Django REST Framework)
- **Database**: SQLite3 (Development), PostgreSQL (Production, planned)
- **Object Storage**: MinIO (Development, S3-compatible), AWS S3 (Production)
- **AI Model**: PyTorch/ONNX (Model), FastAPI (Serving)
- **API**: Django REST Framework (DRF)
- **Deployment**: Docker (with docker-compose)
- **CI/CD**: GitHub Actions

---

## Acknowledgments

This project was initially designed and developed as part of the **CS 30700: Software Engineering I**(Spring 2025) course at Purdue University, West Lafayette. We would like to thank our instructor, TAs for their guidance and support throughout the project.
