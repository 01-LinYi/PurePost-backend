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
    "id": 1,
    "username": "John Doe",
    "email": "email@mail.com",
    "password": "12345678"
  }
  ```

- **Response:**
  Success:

  ```json
  {
    "message": "Account created successfully"
  }
  ```

### 2. User Login

- **URL:** `/auth/login`
- **Method:** `POST`
- **Description:** Authenticates a user and returns a token.
- **Request Body:**

  ```json
  {
    "username": "John Doe",
    "password": "12345678"
  }
  ```

- **Response:**
  Success:

  ```json
  {
    "token": "token.key",
    "user": {
      "id": 1,
      "username": "John doe"
    }
  }
  ```

### 3. User Logout

- **URL:** `/auth/logout`
- **Method:** `POST`
- **Description:** Close auth session and returns a message.
- **Response:**
  Success:

  ```json
  {
    "message": "Logout successfully"
  }
  ```

### 4. Delete User Account

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
    "message": "Account deleted successfully"
  }
  ```

### 5. Retrieve Public Profile

- **URL:** `/users/profiles/<username>`
- **Method:** `GET`
- **Authentication:** Not Required
- **Description:** Retrieve the public profile of a user by their username.

- **Response:**

  ```json
  {
    "username": "John Doe",
    "email": "user@example.com",
    "avatar": "avatars/default.png",
    "bio": "This is user1's bio.",
    "location": "Earth",
    "website": "https://example.com",
    "date_of_birth": "2000-01-01",
    "created_at": "2023-01-01T12:00:00Z",
    "updated_at": "2023-02-01T12:00:00Z",
    "is_active": true
  }
  ```

### 6. Retrieve Logged-In User's Profile

- **URL:** `/users/my-profile/`
- **Method:** `GET`
- **Authentication:** Required
- **Description:** Retrieve the profile of the currently authenticated user.

- **Response:**

  ```json
  {
    "username": "John Doe",
    "email": "user@example.com",
    "avatar": "avatars/default.png",
    "bio": "This is user1's bio.",
    "location": "Earth",
    "website": "https://example.com",
    "date_of_birth": "2000-01-01",
    "created_at": "2023-01-01T12:00:00Z",
    "updated_at": "2023-02-01T12:00:00Z",
    "is_active": true
  }
  ```

### 7. Update User Profile

- **URL:** `/users/update-profile/`
- **Method:** `PUT`
- **Authentication:** Required
- **Description:** Updates the profile of the authenticated user.

- **Request Body:**

  ```json
  {
    "bio": "This is my updated bio.",
    "location": "New York, USA"
  }
  ```

- **Response:**

  ```json
  {
    "username": "John Doe",
    "email": "user@example.com",
    "avatar": "avatars/default.png",
    "bio": "This is my updated bio.",
    "location": "New York, USA",
    "website": "https://example.com",
    "date_of_birth": "2000-01-01",
    "created_at": "2023-01-01T12:00:00Z",
    "updated_at": "2023-02-01T12:00:00Z",
    "is_active": true
  }
  ```

### 8. Get All Posts

- **URL:** `/posts/`
- **Method:** `GET`
- **Description:** Retrieves a list of all posts, ordered by creation time (newest first).
- **Permission:** Authentication required
- **Response:**
  Success (200 OK):

  ```json
  [
    {
      "id": 1,
      "user": 1,
      "content": "Example post content",
      "image": "image.jpg",
      "video": "video.mp4",
      "created_at": "2025-03-01T12:00:00Z",
      "updated_at": "2025-03-01T12:00:00Z"
    },
    ...
  ]
  ```

### 9. Get single Post

- **URL:** `/posts/{id}/`
- **Method:** `GET`
- **Description:** Retrieves details of a specific post by ID.
- **Permission:** Authentication required
- **Response:**
  Success (200 OK):

  ```json
  {
    "id": 1,
    "user": 1,
    "content": "Example post content",
    "image": "image.jpg",
    "video": "video.mp4",
    "created_at": "2025-03-01T12:00:00Z",
    "updated_at": "2025-03-01T12:00:00Z"
  }
  ```

### 10. Create Post

- **URL:** `/posts/`
- **Method:** `POST`
- **Description:** Creates a new post associated with the authenticated user.
- **Permission:** Authentication required
- **Request Body:**

  ```json
  {
    "content": "New post content",
    "image": "Optional image file",
    "video": "Optional video file"
  }
  ```

- **Response:**
  Success (201 Created):

  ```json
  {
    "id": 3,
    "user": 1,
    "content": "New post content",
    "image": "uploaded_image.jpg",
    "video": "uploaded_video.mp4",
    "created_at": "2025-03-03T15:30:00Z",
    "updated_at": "2025-03-03T15:30:00Z"
  }
  ```

### 11. Update Post

- **URL:** `/posts/{id}/`
- **Method:** `PUT/PATCH`
- **Description:** Updates a specific post by ID. Only the post creator can perform this action.
- **Permission:** Authentication required and post ownership
- **Request Body:**

  ```json
  {
    "content": "Updated content",
    "image": "Optional new image",
    "video": "Optional new video"
  }
  ```

- **Response:**
  Success (200 OK):

  ```json
  {
    "id": 1,
    "user": 1,
    "content": "Updated content",
    "image": "new_image.jpg",
    "video": "new_video.mp4",
    "created_at": "2025-03-01T12:00:00Z",
    "updated_at": "2025-03-03T16:45:00Z"
  }
  ```

  Error (403 Forbidden):

  ```json
  {
    "error": "You do not have permission to edit this post."
  }
  ```

### 12. Delete Post

- **URL:** `/posts/{id}/`
- **Method:** `DELETE`
- **Description:** Deletes a specific post by ID. Only the post creator can perform this action.
- **Permission:** Authentication required and post ownership
- **Response:**
  Success (204 No Content)

  Error (403 Forbidden):

  ```json
  {
    "error": "You do not have permission to delete this post."
  }
  ```

### 13. Get All Folders

- **URL:** `/folders/`
- **Method:** `GET`
- **Description:** Retrieves all folders belonging to the current user.
- **Permission:** Authentication required
- **Response:**
  Success (200 OK):

  ```json
  [
    {
      "id": 1,
      "user": 1,
      "name": "Favorites",
      "created_at": "2025-02-15T10:20:00Z"
    },
    {
      "id": 2,
      "user": 1,
      "name": "Interesting Content",
      "created_at": "2025-03-01T09:15:00Z"
    },
    ...
  ]
  ```

### 14. Get Single Folder

- **URL:** `/folders/{id}/`
- **Method:** `GET`
- **Description:** Retrieves details of a specific folder by ID.
- **Permission:** Authentication required and folder ownership
- **Response:**
  Success (200 OK):

  ```json
  {
    "id": 1,
    "user": 1,
    "name": "Favorites",
    "created_at": "2025-02-15T10:20:00Z"
  }
  ```

### 15. Create Folder

- **URL:** `/folders/`
- **Method:** `POST`
- **Description:** Creates a new folder associated with the authenticated user.
- **Permission:** Authentication required
- **Request Body:**

  ```json
  {
    "name": "New Folder"
  }
  ```

- **Response:**
  Success (201 Created):

  ```json
  {
    "id": 3,
    "user": 1,
    "name": "New Folder",
    "created_at": "2025-03-03T17:20:00Z"
  }
  ```

### 16. Update Folder

- **URL:** `/folders/{id}/`
- **Method:** `PUT/PATCH`
- **Description:** Updates the name of a specific folder by ID.
- **Permission:** Authentication required and folder ownership
- **Request Body:**

  ```json
  {
    "name": "Updated Folder Name"
  }
  ```

- **Response:**
  Success (200 OK):

  ```json
  {
    "id": 1,
    "user": 1,
    "name": "Updated Folder Name",
    "created_at": "2025-02-15T10:20:00Z"
  }
  ```

### 17. Delete Folder

- **URL:** `/folders/{id}/`
- **Method:** `DELETE`
- **Description:** Deletes a specific folder by ID.
- **Permission:** Authentication required and folder ownership
- **Response:**
  Success (204 No Content)

### 18. Get All Saved Posts

- **URL:** `/saved-posts/`
- **Method:** `GET`
- **Description:** Retrieves all posts saved by the current user.
- **Permission:** Authentication required
- **Response:**
  Success (200 OK):

  ```json
  [
    {
      "id": 1,
      "user": 1,
      "post": 5,
      "folder": 2,
      "saved_at": "2025-03-02T14:30:00Z"
    },
    {
      "id": 2,
      "user": 1,
      "post": 8,
      "folder": 1,
      "saved_at": "2025-03-02T18:45:00Z"
    },
    ...
  ]
  ```

### 19. Get Single Saved Post

- **URL:** `/saved-posts/{id}/`
- **Method:** `GET`
- **Description:** Retrieves details of a specific saved post record by ID.
- **Permission:** Authentication required and record ownership
- **Response:**
  Success (200 OK):

  ```json
  {
    "id": 1,
    "user": 1,
    "post": 5,
    "folder": 2,
    "saved_at": "2025-03-02T14:30:00Z"
  }
  ```

### 20. Save Post

- **URL:** `/saved-posts/`
- **Method:** `POST`
- **Description:** Saves a post to a specified folder.
- **Permission:** Authentication required
- **Request Body:**

  ```json
  {
    "post_id": 15,
    "folder_id": 3
  }
  ```

- **Response:**
  Success (201 Created):

  ```json
  {
    "id": 5,
    "user": 1,
    "post": 15,
    "folder": 3,
    "saved_at": "2025-03-03T19:10:00Z"
  }
  ```

  Error (404 Not Found) - When post or folder doesn't exist:

  ```json
  {
    "detail": "Not found."
  }
  ```

### 21. Delete Saved Post

- **URL:** `/saved-posts/{id}/`
- **Method:** `DELETE`
- **Description:** Deletes a specific saved post record by ID (unsaves a post).
- **Permission:** Authentication required and record ownership
- **Response:**
  Success (204 No Content)
