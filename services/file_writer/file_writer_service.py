"""
File Writer Service

Subscribes to output WebSocket and writes analysis results to files.
"""
import websockets
import json
import asyncio
import yaml
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class FileWriterService:
    """
    File writer service that subscribes to output WebSocket and writes
    analysis results to files.

    Supports:
    - JSON and JSONL formats
    - Date-based file rotation
    - Automatic directory creation
    - Reconnection on failures
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize file writer service

        Args:
            config_path: Path to configuration file
        """
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.logger = logging.getLogger(__name__)
        self.output_dir = Path(self.config['output']['directory'])
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Statistics
        self.stats = {
            'total_results_written': 0,
            'total_bytes_written': 0,
            'errors': 0,
            'reconnections': 0
        }

    def get_output_filename(self) -> Path:
        """
        Get current output filename based on date pattern

        Returns:
            Path to output file
        """
        pattern = self.config['output']['file_pattern']
        date_str = datetime.now().strftime("%Y%m%d")
        filename = pattern.replace("{date}", date_str)
        return self.output_dir / filename

    async def write_result(self, result: Dict[Any, Any]):
        """
        Write result to file

        Args:
            result: Analysis result dictionary to write
        """
        output_file = self.get_output_filename()
        format_type = self.config['output']['format']

        try:
            if format_type == 'jsonl':
                # Append as JSON Lines (one JSON per line)
                with open(output_file, 'a') as f:
                    line = json.dumps(result, default=str) + '\n'
                    f.write(line)
                    self.stats['total_bytes_written'] += len(line.encode('utf-8'))

            elif format_type == 'json':
                # Append to JSON array
                results = []
                if output_file.exists():
                    try:
                        with open(output_file, 'r') as f:
                            results = json.load(f)
                    except json.JSONDecodeError:
                        self.logger.warning(f"Could not parse existing file {output_file}, starting fresh")
                        results = []

                results.append(result)

                with open(output_file, 'w') as f:
                    content = json.dumps(results, indent=2, default=str)
                    f.write(content)
                    self.stats['total_bytes_written'] += len(content.encode('utf-8'))

            else:
                self.logger.error(f"Unknown format type: {format_type}")
                return

            self.stats['total_results_written'] += 1
            self.logger.info(
                f"✓ Wrote result to {output_file.name} "
                f"({self.stats['total_results_written']} total)"
            )

            # Check file rotation
            await self._check_rotation(output_file)

        except Exception as e:
            self.logger.error(f"Failed to write result: {e}")
            self.stats['errors'] += 1

    async def _check_rotation(self, output_file: Path):
        """
        Check if file rotation is needed based on size

        Args:
            output_file: Current output file path
        """
        if not self.config['output']['rotation']['enabled']:
            return

        max_size_bytes = self.config['output']['rotation']['max_size_mb'] * 1024 * 1024

        if output_file.exists() and output_file.stat().st_size > max_size_bytes:
            # Rotate file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated_name = f"{output_file.stem}_{timestamp}{output_file.suffix}"
            rotated_path = output_file.parent / rotated_name

            try:
                output_file.rename(rotated_path)
                self.logger.info(f"↻ Rotated file to {rotated_name}")
            except Exception as e:
                self.logger.error(f"Failed to rotate file: {e}")

    async def run(self):
        """
        Subscribe to output WebSocket and write results

        Main loop that:
        1. Connects to output WebSocket
        2. Listens for analysis results
        3. Writes results to files
        4. Handles reconnection on failures
        """
        ws_url = self.config['websocket']['url']
        reconnect_interval = self.config['websocket'].get('reconnect_interval_seconds', 5)

        self.logger.info(f"File Writer Service starting...")
        self.logger.info(f"   WebSocket: {ws_url}")
        self.logger.info(f"   Output directory: {self.output_dir}")
        self.logger.info(f"   Format: {self.config['output']['format']}")

        while True:
            try:
                self.logger.info(f"Connecting to {ws_url}...")
                async with websockets.connect(ws_url) as websocket:
                    self.logger.info("✓ Connected to output WebSocket")

                    async for message in websocket:
                        try:
                            data = json.loads(message)

                            # Handle different message types
                            if data.get('type') == 'analysis_result':
                                await self.write_result(data['data'])

                            elif data.get('type') == 'heartbeat':
                                self.logger.debug("Received heartbeat")

                            else:
                                self.logger.warning(f"Unknown message type: {data.get('type')}")

                        except json.JSONDecodeError as e:
                            self.logger.error(f"Invalid JSON message: {e}")
                            self.stats['errors'] += 1

                        except Exception as e:
                            self.logger.error(f"Error processing message: {e}")
                            self.stats['errors'] += 1

            except websockets.exceptions.ConnectionClosed as e:
                self.logger.warning(f"Connection closed: {e}")
                self.stats['reconnections'] += 1

            except Exception as e:
                self.logger.error(f"Error: {e}")
                self.stats['reconnections'] += 1

            # Reconnect after delay
            self.logger.info(f"Reconnecting in {reconnect_interval}s...")
            await asyncio.sleep(reconnect_interval)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get service statistics

        Returns:
            Dictionary with statistics
        """
        return {
            **self.stats,
            'output_directory': str(self.output_dir),
            'current_file': str(self.get_output_filename())
        }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    writer = FileWriterService()
    asyncio.run(writer.run())
