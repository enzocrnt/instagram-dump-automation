# Instagram Photo Dump Pipeline

A desktop creator studio application built with Python, Eel, and Bootstrap 5 to streamline high-volume chronological image curation and automated slide deck deployment.

## Key Features

- Instagram Styled UI: Soft dark charcoal layout following standard social creator aesthetics.
- Dynamic Local Curation: Rapidly scrapes physical hard drive backups by month and day configurations.
- Chronological Randomizer: One-click pool rerolling utilizing internal shuffling algorithms.
- Standby Queue Vault: Direct internal drive file isolation utilizing STAGED and POSTED prefixes to eliminate SSD wear.
- Automated Date Captions: Pre-populates text fields based on target calendar metrics.
- Selenium Browser Handshaking: Directly pipes curated photo arrays and custom captions straight to the web interface.

## Getting Started

### Prerequisites

Ensure your machine is running Python 3.10 or higher along with a valid Google Chrome installation.

### Installation

1. Clone this repository workspace:
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name

2. Install the application layout dependencies:
pip install eel selenium

### Execution

Run the system initialization script from your project root:
python app.py

Note: On your initial upload run, Selenium will prompt a 300-second window allowing you to log into your account manually to establish your local secure profile session data storage framework.