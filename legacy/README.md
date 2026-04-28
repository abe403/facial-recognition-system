# GymAccess: Facial Recognition Access Control System

GymAccess is a desktop application built with Python that provides a simple yet effective access control system for a gym or similar facility. It uses facial recognition to register, verify, and manage members, ensuring that only authorized individuals with active memberships can gain entry.

## Table of Contents
- [Project Overview](#project-overview)
- [Key Features](#key-features)
- [Screenshots](#screenshots)
- [Technology Stack](#technology-stack)
- [Setup and Installation](#setup-and-installation)
- [How to Run](#how-to-run)
- [File Structure](#file-structure)
- [Future Improvements](#future-improvements)

## Project Overview

The primary goal of GymAccess is to automate the check-in process at a gym. Instead of manual ID checks or key fobs, the system uses a camera to verify a member's identity.

The workflow is straightforward:
1.  **Registration:** New members are registered by inputting their details (Name, Membership ID, Expiration Date) and capturing a clear image of their face.
2.  **Verification:** When a member wishes to enter, they face the camera. The system recognizes them, checks their membership status in the database, and grants or denies access.
3.  **Management:** Administrators can edit member details, update their membership expiration date, or recapture a member's facial data if needed.
4.  **Logging:** All successful entries are logged to a CSV file for record-keeping.

## Key Features

*   👤 **Member Registration:** A user-friendly form to add new members, including facial data capture via a webcam.
*   🔍 **Facial Recognition Verification:** Real-time access verification using OpenCV's LBPH Face Recognizer.
*   ✏️ **Member Data Management:** An interface to edit existing member information or update their facial sample.
*    expiring or already expired.
*   📄 **Access Logging:** Automatically records the date and time of every successful entry into a `acceso_gimnasio.csv` file.
*   ✨ **Modern UI:** A clean, dark-themed graphical user interface built with Tkinter.
*   📂 **Self-Contained:** The application creates and manages its own SQLite database and image sample directories.

## Technology Stack

*   **Language:** Python 3
*   **GUI:** [Tkinter](https://docs.python.org/3/library/tkinter.html) (standard Python library) for the desktop interface.
*   **Computer Vision:** [OpenCV](https://opencv.org/) (`opencv-python`) for face detection (Haar Cascades) and recognition (LBPH Face Recognizer).
*   **Database:** [SQLite 3](https://www.sqlite.org/index.html) (standard Python library) for storing member data.
*   **Image Processing:** [Pillow (PIL)](https://python-pillow.org/) to integrate OpenCV images with the Tkinter UI.
*   **Numerical Operations:** [NumPy](https://numpy.org/) for handling image arrays.

## Setup and Installation

Follow these steps to get the application running on your local machine.

**Prerequisites:**
*   Python 3.8 or newer
*   A webcam connected to your computer

**1. Clone the repository:**
```bash
git clone https://github.com/your-username/GymAccess.git
cd GymAccess
```

**2. Create and activate a virtual environment (recommended):**

*   On macOS/Linux:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
*   On Windows:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

**3. Install the required dependencies:**
A `requirements.txt` file is included for easy installation.
```bash
pip install -r requirements.txt
```
*(If you don't have a `requirements.txt` file, create one with the following content or install manually):*
```
# requirements.txt
opencv-python
numpy
Pillow
```

**4. Haar Cascade File:**
The application uses the `haarcascade_frontalface_default.xml` file for face detection. The script attempts to locate it automatically from the installed OpenCV library. If it fails, you may need to download it and place it in the project's root directory.

## How to Run

Once the setup is complete, you can run the application with a single command:

```bash
python frs_0.0.0.3.py
```

The main application window should appear. From there, you can start registering, verifying, and editing members.

## File Structure

The application will automatically create the following files and directories in the project root upon first run:

```
/
├── frs_0.0.0.3.py        # Main application script
├── README.md             # This readme file
├── requirements.txt      # Project dependencies
│
├── face_samples/         # (Auto-created) Stores captured face images (e.g., 'MEMBER_ID.png')
├── members.db            # (Auto-created) SQLite database for member data
└── acceso_gimnasio.csv   # (Auto-created) Log of all successful entries
```
