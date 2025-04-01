# varis-utils
Custom Redbot COGS

## NWSSHUTDOWN
Automatically shuts down your server in the event of a Tornado or Severe Thunderstorm warning. This cog monitors weather alerts from the National Weather Service (NWS) and takes action to ensure server safety during severe weather conditions. Features include:
- Configurable weather alert types.
- Admin notifications for severe weather.
- Automated server shutdown with a countdown timer.
- Current weather conditions and mesoscale discussions.

## announcements
Provides live server status announcements for FiveM. This cog allows server administrators to update and broadcast the current status of their FiveM server. Features include:
- Real-time status updates.
- Integration with a Flask API for external access to the latest announcements.

## Installation
To install these cogs, add this repository to your Redbot instance and install the desired cogs.

```bash
[p]repo add varis-utils https://github.com/dasKreuzer/varis-utils
[p]cog install varis-utils nwsshutdown
[p]cog install varis-utils announcements
[p]load nwsshutdown
[p]load announcements
```

Replace `[p]` with your bot's command prefix.

## Linux Setup
Follow these steps to set up the cogs on a Linux environment:

1. **Install Python and Pip**:
   Ensure Python 3.8+ and pip are installed:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip
   ```

2. **Install Redbot**:
   Install Redbot using pip:
   ```bash
   pip3 install Red-DiscordBot
   ```

3. **Create a Bot Instance**:
   Create a new Redbot instance:
   ```bash
   redbot-setup
   ```

4. **Clone the Repository**:
   Clone this repository to your server:
   ```bash
   git clone https://github.com/dasKreuzer/varis-utils.git
   cd varis-utils
   ```

5. **Install Required Dependencies**:
   Install the required Python packages:
   ```bash
   pip3 install -r requirements.txt
   ```

6. **Run Redbot**:
   Start your Redbot instance:
   ```bash
   redbot <your-instance-name>
   ```

7. **Add and Load the Cogs**:
   Use the commands below to add the repository and load the cogs:
   ```bash
   [p]repo add varis-utils https://github.com/dasKreuzer/varis-utils
   [p]cog install varis-utils nwsshutdown
   [p]cog install varis-utils announcements
   [p]load nwsshutdown
   [p]load announcements
   ```

8. **Optional: Run Flask API for Announcements**:
   If using the `announcements` cog, ensure Flask is running:
   ```bash
   python3 -m flask run --host=0.0.0.0 --port=8765
   ```
   You can use a process manager like `screen` or `tmux` to keep it running in the background.
