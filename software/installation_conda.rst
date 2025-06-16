.. title:: Installation Guide for Conda/Miniconda/Miniforge on Windows/macOS

===============================================
Installation of Conda, Miniconda, and Miniforge
===============================================

A streamlined guide to installing Conda and its variants—Anaconda, Miniconda, and Miniforge—on both Windows and macOS is essential for anyone in the data science and programming fields. These tools provide robust environment and package management, ensuring reproducibility and simplifying collaboration.

Choosing Your Distribution
==========================

Before diving into the installation, it's crucial to understand the differences between the available distributions:

- **Anaconda**: The full-featured, comprehensive distribution. It has a large initial download size and comes pre-loaded with a vast array of data science packages. This is ideal for beginners or those who prefer having a complete setup from the start.

- **Miniconda**: A minimal installer for Conda. It includes only the Conda package manager, Python, and their essential dependencies. This is the perfect choice for users who want to create custom environments and install only the packages they need, resulting in a smaller footprint.

- **Miniforge**: A community-driven alternative to Miniconda that uses conda-forge as the default channel. This ensures access to the latest community-maintained packages and is the recommended choice for M1/M2 Mac users due to its native support for Apple Silicon.

Installation on Windows
=======================

The installation process on Windows is straightforward, typically involving a graphical installer.

Anaconda
--------

1. **Download the Installer**: Navigate to the `Anaconda Distribution <https://www.anaconda.com/products/distribution>`_ website and download the installer for Windows.
2. **Run the Installer**: Double-click the downloaded ``.exe`` file to launch the installation wizard.
3. **Follow On-Screen Instructions**:
   - Agree to the license agreement.
   - Select "Just Me" for a per-user installation (recommended).
   - Choose an installation directory (the default is usually fine).
   - **Do not add Anaconda to your PATH** environment variable. This can interfere with other software. Instead, use the **Anaconda Prompt** to access Conda.
4. **Complete Installation**: Once complete, you can find the **Anaconda Prompt** in your Start Menu.

Miniconda
---------

1. **Download the Installer**: Go to the `Miniconda documentation <https://docs.conda.io/en/latest/miniconda.html>`_ and download the latest Windows installer.
2. **Run the Installer**: Execute the downloaded ``.exe`` file.
3. **Follow On-Screen Instructions**: The steps are similar to the Anaconda installation. It is still recommended not to add Miniconda to your PATH and to use the **Miniconda Prompt** for all Conda-related commands.

Miniforge
---------

1. **Download the Installer**: Visit the `Miniforge GitHub repository <https://github.com/conda-forge/miniforge>`_ and download the latest ``Miniforge3-Windows-x86_64.exe`` installer.
2. **Run the Installer**: Launch the downloaded executable.
3. **Follow On-Screen Instructions**: Accept the default settings. You will now have a **Miniforge Prompt** available in your Start Menu.

Installation on macOS
=====================

On macOS, you have the option of using a graphical installer or the command line, which offers more flexibility.

Anaconda
--------

1. **Download the Installer**: Head to the `Anaconda Distribution <https://www.anaconda.com/products/distribution>`_ page and download the appropriate installer for your Mac's architecture (Intel or Apple Silicon).
2. **Run the Installer**: Double-click the downloaded ``.pkg`` file.
3. **Follow On-Screen Instructions**:
   - Proceed through the license agreement.
   - Choose the installation location.
   - The installer will automatically run the necessary shell script to initialize Conda.
4. **Verify Installation**: Open a new Terminal window. You should see ``(base)`` preceding your command prompt, indicating the base Conda environment is active.

Miniconda
---------

For macOS, using the command-line installer is common.

**Download the Installer**: Open your Terminal and use ``curl`` to download the installer:

- **Apple Silicon (M1/M2)**:

  .. code-block:: bash

     curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh

- **Intel**:

  .. code-block:: bash

     curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh

**Run the Installer Script**:

.. code-block:: bash

   bash Miniconda3-latest-MacOSX-*.sh

**Follow the Prompts**:

- Press Enter to review the license agreement.
- Type ``yes`` to agree to the terms.
- Press Enter to confirm the installation location.
- Type ``yes`` to initialize Miniconda3.

**Restart Your Terminal**: Close and reopen your Terminal window for the changes to take effect.

Miniforge
---------

Miniforge is highly recommended for Apple Silicon Macs.

1. **Download the Installer**:

   - **Apple Silicon (M1/M2)**:

     .. code-block:: bash

        curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh

   - **Intel**:

     .. code-block:: bash

        curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-x86_64.sh

2. **Run the Installer Script**:

   .. code-block:: bash

      bash Miniforge3-MacOSX-*.sh

3. **Follow the Prompts**: The process is identical to the Miniconda installation.
4. **Restart Your Terminal**: After the installation is complete, restart your Terminal session.

Verifying Your Installation
===========================

Regardless of the distribution or operating system, you can verify a successful installation by opening your respective Conda prompt (Anaconda/Miniconda/Miniforge Prompt on Windows, or Terminal on macOS) and running:

.. code-block:: bash

   conda --version

This command should return the installed version of Conda, confirming that your installation was successful. You can then proceed to create and manage your environments.
