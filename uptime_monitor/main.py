"""
Main entry point for Simple Uptime Monitor.
Starts both the monitoring scheduler and Flask web server.
"""

import sys
import signal
import logging
from threading import Event

from uptime_monitor.config import load_config
from uptime_monitor.database import init_database
from uptime_monitor.scheduler import MonitorScheduler
from uptime_monitor.webapp import app, init_app

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('data/uptime-monitor.log')
    ]
)

logger = logging.getLogger(__name__)

# Global shutdown event
shutdown_event = Event()
scheduler = None


def get_scheduler():
    """Get the global scheduler instance"""
    return scheduler


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    shutdown_event.set()

    if scheduler:
        scheduler.stop()

    sys.exit(0)


def main():
    """Main application entry point"""
    global scheduler

    try:
        logger.info("=" * 60)
        logger.info("Simple Uptime Monitor starting...")
        logger.info("=" * 60)

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Load configuration
        logger.info("Loading configuration...")
        config = load_config('config.yaml')

        # Initialize database
        logger.info("Initializing database...")
        db_path = config.get_database_path()
        init_database(f"sqlite:///{db_path}")

        # Initialize Flask app
        logger.info("Initializing web application...")
        init_app()

        # Start monitoring scheduler
        logger.info("Starting monitor scheduler...")
        scheduler = MonitorScheduler(max_workers=10)
        scheduler.start()

        # Store scheduler reference in Flask app for access from routes
        app.config['SCHEDULER'] = scheduler

        # Get web server configuration
        web_config = config.get_web_config()
        host = web_config['host']
        port = web_config['port']

        logger.info("=" * 60)
        logger.info(f"Simple Uptime Monitor is running!")
        logger.info(f"Web dashboard: http://{host if host != '0.0.0.0' else 'localhost'}:{port}")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)

        # Start Flask web server (blocking)
        app.run(
            host=host,
            port=port,
            debug=False,
            use_reloader=False,  # Disable reloader to avoid duplicate scheduler
            threaded=True
        )

    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        logger.error("Please create config.yaml from config.example.yaml")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if scheduler:
            scheduler.stop()


if __name__ == '__main__':
    main()
