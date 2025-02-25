# API Documentation

## Overview

This document provides an overview of the APIs available in the PurePost-backend project. Each API endpoint is described with its purpose, request method, URL, parameters, and response format.

## Endpoints

### 1. User Registration

- **URL:** `/auth/register`
- **Method:** `POST`
- **Description:** Registers a new user.
- **Request Body:**

  ```json
  {
    // TODO
  }
  ```

- **Response:**

  ```json
  {
    // TODO
  }
  ```

### 2. User Login

- **URL:** `/auth/login`
- **Method:** `POST`
- **Description:** Authenticates a user and returns a token.
- **Request Body:**

  ```json
  {
    // TODO
  }
  ```

- **Response:**

  ```json
  {
    // TODO
  }
  ```

### 3. Delete User Account

- **URL:** `/auth/delete-account`
- **Method:** `POST`
- **Description:** Deletes the authenticated user's account.
- **Headers:**

  ```json
  {
    // TODO
  }
  ```

- **Response:**

  ```json
  {
    // TODO
  }
  ```

### 4. Retrieve Public Profile

- **URL:** `/users/profiles/<username>`
- **Method:** `GET`
- **Authentication:** Not Required
- **Description:** Retrieve the public profile of a user by their username.

- **Response:**

  ```json
  {
    "username": "John Doe",
    "avatar": "avatars/default.png",
    "bio": "This is user1's bio.",
    "location": "Earth",
    "website": "https://example.com",
    "date_of_birth": "2000-01-01",
    "created_at": "2023-01-01T12:00:00Z",
    "updated_at": "2023-02-01T12:00:00Z"
  }
  ```

### 5. Retrieve Logged-In User's Profile

- **URL:** `/users/my-profile/`
- **Method:** `GET`
- **Authentication:** Required
- **Description:** Retrieve the profile of the currently authenticated user.

- **Headers:**

  ```json
  {
    "Authorization": "Token abc123xyz",
  }
  ```

- **Response:**

  ```json
  {
    "username": "John Doe",
    "avatar": "avatars/default.png",
    "bio": "This is user1's bio.",
    "location": "Earth",
    "website": "https://example.com",
    "date_of_birth": "2000-01-01",
    "created_at": "2023-01-01T12:00:00Z",
    "updated_at": "2023-02-01T12:00:00Z"
  }
  ```

### 6. Update User Profile

- **URL:** `/users/update-profile/`
- **Method:** `PUT`
- **Authentication:** Required
- **Description:** Updates the profile of the authenticated user.
- **Headers:**

  ```json
  {
    "Authorization": "Token abc123xyz",
    "Content-Type": "application/json",
  }
  ```

- **Request Body:**

  ```json
  {
    "bio": "This is my updated bio.",
    "location": "New York, USA",
  }
  ```

- **Response:**

  ```json
  {
    "username": "John Doe",
    "avatar": "avatars/default.png",
    "bio": "This is my updated bio.",
    "location": "New York, USA",
    "website": "https://example.com",
    "date_of_birth": "2000-01-01",
    "created_at": "2023-01-01T12:00:00Z",
    "updated_at": "2023-02-01T12:00:00Z"
  }
  ```
