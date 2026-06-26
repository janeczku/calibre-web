# Qalibre

Qalibre is a web app that offers a clean and intuitive interface for browsing, reading, and downloading eBooks using a valid [Calibre](https://calibre-ebook.com) database.

[![License](https://img.shields.io/github/license/janeczku/calibre-web?style=flat-square)](https://github.com/janeczku/calibre-web/blob/master/LICENSE)

<details>
<summary><strong>Table of Contents</strong> (click to expand)</summary>

1. [About](#qalibre)
2. [Features](#features)
3. [Installation](#installation)
   - [Build and Run with Docker (Recommended)](#build-and-run-with-docker-recommended)
   - [Manual Installation from Source](#manual-installation-from-source)
4. [Quick Start](#quick-start)
5. [Requirements](#requirements)
6. [Troubleshooting](#troubleshooting)
7. [Contact](#contact)

</details>

*This software is a fork of Calibre-Web and licensed under the GPL v3 License.*

## Features

- Modern and responsive React SPA frontend styled with Palantir Blueprint v6 (Editorial Theme)
- Full graphical setup
- Comprehensive user management with fine-grained per-user permissions
- Admin interface
- Multilingual user interface
- OPDS feed for eBook reader apps
- Advanced search and filtering options
- Custom book collection (shelves) creation
- eBook metadata editing and deletion support
- eBook conversion through Calibre binaries
- eBook download restriction to logged-in users
- Public user registration support
- Send eBooks to E-Readers with a single click
- Sync Kobo devices with your Calibre library
- In-browser eBook reading support for multiple formats
- Upload new books in various formats, including audio formats
- Calibre Custom Columns support
- Content hiding based on categories and Custom Column content per user

## Installation

This version of Qalibre features a rebuilt, modern **React SPA frontend** styled with **Palantir Blueprint v6 (Editorial Theme)**. To run this configuration, you must build the frontend assets before starting the Python server, or use the provided Docker integration.

### Build and Run with Docker (Recommended)

1. **Build the Docker Image**:
   ```bash
   docker build -t qalibre-spa .
   ```
2. **Run the Container**:
   ```bash
   docker run -d -p 8083:8083 --name qalibre -v /path/to/calibre/library:/library qalibre-spa
   ```

### Manual Installation from Source

#### Step 1: Build the React Frontend SPA
Ensure you have **Node.js 20+** installed.
1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm ci
   ```
3. Compile the production bundle:
   ```bash
   npm run build
   ```
4. Return to the root folder:
   ```bash
   cd ..
   ```
This generates the SPA assets under `frontend/dist/` which the Flask app will serve.

#### Step 2: Install and Start the Python Backend
1. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv qalibre-env
   source qalibre-env/bin/activate
   ```
2. **Install requirements**:
   ```bash
   pip install -r requirements.txt
   pip install -r optional-requirements.txt
   ```
3. **Start Qalibre**:
   ```bash
   python cps.py
   ```

## Quick Start

1. **Access Qalibre**: Open your browser and navigate to:
   ```
   http://localhost:8083
   ```
   or for the OPDS catalog:
   ```
   http://localhost:8083/opds
   ```
2. **Log in**: Use the default admin credentials:
   - **Username:** admin
   - **Password:** admin123
3. **Database Setup**: If you do not have a Calibre database, download a sample from:
   ```
   https://github.com/janeczku/calibre-web/raw/master/library/metadata.db
   ```
   Move it out of the Qalibre folder to avoid overwriting during updates.
4. **Configure Calibre Database**: In the admin interface, set the `Location of Calibre database` to the path of the folder containing your Calibre library (where `metadata.db` is located) and click "Save".
5. **Google Drive Integration**: For hosting your Calibre library on Google Drive, refer to the Google Drive integration guides.
6. **Admin Configuration**: Configure your instance via the admin page.

## Requirements

- **Python Version**: Ensure you have Python 3.7 or newer.
- **Imagemagick**: Required for cover extraction from EPUBs.
- **Optional Tools**:
   - **Calibre desktop program**: Recommended for on-the-fly conversion and metadata editing.
   - **Kepubify tool**: Needed for Kobo device support.

## Troubleshooting

- **Common Issues**: 
   - If you experience issues starting the application, check the log files located in the `logs` directory for error messages.
   - If eBooks fail to load, verify that the `Location of Calibre database` is correctly set and that the database file is accessible.
   - You need to enable uploads under `Basic settings` for this option to appear.

## Contact

Join us on [Discord](https://discord.gg/h2VsJ2NEfB)

---

Thank you for using Qalibre! We hope you enjoy managing your eBook library with our tool.
