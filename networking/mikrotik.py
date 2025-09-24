import logging
import traceback
from contextlib import contextmanager
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from librouteros import connect
from librouteros.exceptions import LibRouterosError
from .models import ActiveSession, PausedSession, SessionStatus

# Configure logging
logger = logging.getLogger(__name__)

class MikrotikSessionManager:
    """
    Manages Mikrotik session integration with the billing system.
    Handles creating, updating, and terminating user sessions on Mikrotik routers.
    """
    
    def __init__(self, host=None, username=None, password=None, port=8728):
        """
        Initialize Mikrotik session manager.
        
        Args:
            host (str): Mikrotik router IP address
            username (str): Mikrotik API username
            password (str): Mikrotik API password
            port (int): Mikrotik API port (default: 8728)
        """
        self.host = host or getattr(settings, 'MIKROTIK_HOST', '192.168.88.1')
        self.username = username or getattr(settings, 'MIKROTIK_USERNAME', 'admin')
        self.password = password or getattr(settings, 'MIKROTIK_PASSWORD', '')
        self.port = port
        self.connection = None
    
    @contextmanager
    def mikrotik_connection(self):
        """
        Context manager for Mikrotik connection.
        Ensures connection is properly closed even if an error occurs.
        """
        try:
            if not self.connection:
                self.connect()
            yield
        except Exception as e:
            logger.error(f"Error in Mikrotik connection context: {str(e)}\n{traceback.format_exc()}")
            raise
        finally:
            self.disconnect()
    
    def connect(self):
        """
        Establish connection to Mikrotik router.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.connection = connect(
                username=self.username,
                password=self.password,
                host=self.host,
                port=self.port
            )
            logger.info(f"Successfully connected to Mikrotik router at {self.host}")
            return True
        except LibRouterosError as e:
            logger.error(f"Failed to connect to Mikrotik router: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to Mikrotik router: {str(e)}\n{traceback.format_exc()}")
            return False
    
    def disconnect(self):
        """
        Close connection to Mikrotik router.
        """
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Disconnected from Mikrotik router")
        return True
    
    def create_session(self, session_id, username, password, data_limit_mb=None, 
                      upload_speed_mbps=None, download_speed_mbps=None):
        """
        Create a new user session on Mikrotik router with speed control.
        
        Args:
            session_id (int): The ID of the ActiveSession in the database
            username (str): Username for the session
            password (str): Password for the session
            data_limit_mb (int, optional): Data limit in MB
            upload_speed_mbps (int, optional): Upload speed limit in Mbps
            download_speed_mbps (int, optional): Download speed limit in Mbps
            
        Returns:
            bool: True if session created successfully, False otherwise
        """
        try:
            with self.mikrotik_connection():
                # Create user in Mikrotik
                user_path = self.connection.path('/user')
                user_path.add(
                    name=username,
                    password=password,
                    group='billing-users'  # Assuming you have a group for billing users
                )
                
                # Create queue for bandwidth limiting and speed control
                queue_path = self.connection.path('/queue/simple')
                
                # Set default speeds if not provided
                if not upload_speed_mbps:
                    upload_speed_mbps = 10  # Default 10 Mbps upload
                if not download_speed_mbps:
                    download_speed_mbps = 50  # Default 50 Mbps download
                
                queue_config = {
                    'name': f"session-{session_id}-{username}",
                    'target': f"{username}",
                    'max-limit': f"{download_speed_mbps}M/{upload_speed_mbps}M"
                }
                
                # Note: limit-at is for guaranteed bandwidth, not data cap
                # If you want to enforce a data cap, you need to use Mikrotik's scripting
                # or radius accounting, as queues alone do not cap data.
                
                queue_path.add(**queue_config)
                
                logger.info(f"Created Mikrotik session for user {username} (session ID: {session_id}) with speeds: {download_speed_mbps}M/{upload_speed_mbps}M")
                return True
        except LibRouterosError as e:
            logger.error(f"Failed to create Mikrotik session for user {username}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating Mikrotik session for user {username}: {str(e)}\n{traceback.format_exc()}")
            return False
    
    def update_session_data(self, session_id, username, data_used_mb):
        """
        Update session data usage on Mikrotik router.
        
        Args:
            session_id (int): The ID of the ActiveSession in the database
            username (str): Username for the session
            data_used_mb (int): Data used in MB
            
        Returns:
            bool: True if session updated successfully, False otherwise
        """
        try:
            with self.mikrotik_connection():
                # Update data usage in our database
                try:
                    session = ActiveSession.objects.get(id=session_id)
                    session.data_used_mb = data_used_mb
                    session.save()
                    
                    # Update subscription data usage
                    if session.subscription:
                        session.subscription.data_used_mb += data_used_mb
                        session.subscription.save()
                    
                    logger.info(f"Updated data usage for session {session_id}: {data_used_mb} MB")
                except ActiveSession.DoesNotExist:
                    logger.error(f"ActiveSession with ID {session_id} does not exist")
                    return False
                
                # Here you could also update Mikrotik-specific data tracking if needed
                # For example, updating counters or sending notifications
                
                return True
        except Exception as e:
            logger.error(f"Failed to update session data for session {session_id}: {str(e)}\n{traceback.format_exc()}")
            return False
    
    def terminate_session(self, session_id, username):
        """
        Terminate a user session on Mikrotik router.
        
        Args:
            session_id (int): The ID of the ActiveSession in the database
            username (str): Username for the session
            
        Returns:
            bool: True if session terminated successfully, False otherwise
        """
        try:
            with self.mikrotik_connection():
                # Remove user from Mikrotik
                user_path = self.connection.path('/user')
                users = user_path.select().where(name=username)
                
                # Check if users exist before trying to remove them
                users_list = list(users)
                if users_list:
                    for user in users_list:
                        user_path.remove(user['.id'])
                    logger.info(f"Removed user {username} from Mikrotik")
                else:
                    logger.warning(f"User {username} not found on Mikrotik")
                
                # Remove associated queue if it exists
                queue_path = self.connection.path('/queue/simple')
                queues = queue_path.select().where(name__contains=f"session-{session_id}")
                
                # Check if queues exist before trying to remove them
                queues_list = list(queues)
                if queues_list:
                    for queue in queues_list:
                        queue_path.remove(queue['.id'])
                    logger.info(f"Removed queue for session {session_id} from Mikrotik")
                else:
                    logger.warning(f"Queue for session {session_id} not found on Mikrotik")
                
                # Update session status in database
                try:
                    session = ActiveSession.objects.get(id=session_id)
                    session.terminate_session()
                    logger.info(f"Terminated session {session_id} for user {username}")
                except ActiveSession.DoesNotExist:
                    logger.warning(f"ActiveSession with ID {session_id} does not exist in database")
                
                return True
        except LibRouterosError as e:
            logger.error(f"Failed to terminate Mikrotik session for user {username}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error terminating Mikrotik session for user {username}: {str(e)}\n{traceback.format_exc()}")
            return False
    
    def pause_session(self, session_id, username, pause_reason=None, user=None):
        """
        Pause a user session on Mikrotik router.
        
        Args:
            session_id (int): The ID of the ActiveSession in the database
            username (str): Username for the session
            pause_reason (str, optional): Reason for pausing the session
            user (User, optional): User who initiated the pause
            
        Returns:
            bool: True if session paused successfully, False otherwise
        """
        try:
            with self.mikrotik_connection():
                # Get the session
                try:
                    session = ActiveSession.objects.get(id=session_id)
                except ActiveSession.DoesNotExist:
                    logger.error(f"ActiveSession with ID {session_id} does not exist")
                    return False
                
                if session.is_paused:
                    logger.warning(f"Session {session_id} is already paused")
                    return False
                
                # Disable the user's queue to pause bandwidth
                queue_path = self.connection.path('/queue/simple')
                queues = queue_path.select().where(name__contains=f"session-{session_id}")
                
                # Check if queues exist before trying to modify them
                queues_list = list(queues)
                if queues_list:
                    for queue in queues_list:
                        queue_path.set(
                            queue['.id'],
                            **{'disabled': 'true'}
                        )
                    logger.info(f"Disabled queue for session {session_id} on Mikrotik")
                else:
                    logger.warning(f"Queue for session {session_id} not found on Mikrotik")
                
                # Update session status
                session.pause_session()
                
                # Create pause history record
                PausedSession.objects.create(
                    session=session,
                    pause_reason='user_request' if not pause_reason else 'admin_action',
                    pause_description=pause_reason or 'Session paused',
                    paused_by=user
                )
                
                logger.info(f"Paused session {session_id} for user {username}")
                return True
                
        except LibRouterosError as e:
            logger.error(f"Failed to pause Mikrotik session for user {username}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error pausing Mikrotik session for user {username}: {str(e)}\n{traceback.format_exc()}")
            return False
    
    def resume_session(self, session_id, username):
        """
        Resume a paused user session on Mikrotik router.
        
        Args:
            session_id (int): The ID of the ActiveSession in the database
            username (str): Username for the session
            
        Returns:
            bool: True if session resumed successfully, False otherwise
        """
        try:
            with self.mikrotik_connection():
                # Get the session
                try:
                    session = ActiveSession.objects.get(id=session_id)
                except ActiveSession.DoesNotExist:
                    logger.error(f"ActiveSession with ID {session_id} does not exist")
                    return False
                
                if not session.is_paused:
                    logger.warning(f"Session {session_id} is not paused")
                    return False
                
                # Enable the user's queue to resume bandwidth
                queue_path = self.connection.path('/queue/simple')
                queues = queue_path.select().where(name__contains=f"session-{session_id}")
                
                # Check if queues exist before trying to modify them
                queues_list = list(queues)
                if queues_list:
                    for queue in queues_list:
                        queue_path.set(
                            queue['.id'],
                            **{'disabled': 'false'}
                        )
                    logger.info(f"Enabled queue for session {session_id} on Mikrotik")
                else:
                    logger.warning(f"Queue for session {session_id} not found on Mikrotik")
                
                # Update session status
                session.resume_session()
                
                # Update the latest pause history record
                latest_pause = PausedSession.objects.filter(
                    session=session,
                    resumed_at__isnull=True
                ).first()
                
                if latest_pause:
                    latest_pause.resume()
                
                logger.info(f"Resumed session {session_id} for user {username}")
                return True
                
        except LibRouterosError as e:
            logger.error(f"Failed to resume Mikrotik session for user {username}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error resuming Mikrotik session for user {username}: {str(e)}\n{traceback.format_exc()}")
            return False
    
    def get_session_status(self, session_id):
        """
        Get the current status of a session including pause information.
        
        Args:
            session_id (int): The ID of the ActiveSession in the database
            
        Returns:
            dict: Session status information or None if error
        """
        try:
            session = ActiveSession.objects.get(id=session_id)
            
            status = {
                'session_id': session.id,
                'username': session.user.phone_number,
                'is_active': session.is_active,
                'is_paused': session.is_paused,
                'data_used_mb': session.data_used_mb,
                'start_time': session.start_time,
                'pause_history': []
            }
            
            # Get pause history
            pause_history = PausedSession.objects.filter(session=session)[:5]
            for pause in pause_history:
                status['pause_history'].append({
                    'paused_at': pause.paused_at,
                    'resumed_at': pause.resumed_at,
                    'pause_duration': pause.pause_duration,
                    'pause_reason': pause.pause_reason
                })
            
            return status
            
        except ActiveSession.DoesNotExist:
            logger.error(f"ActiveSession with ID {session_id} does not exist")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting session status for {session_id}: {str(e)}\n{traceback.format_exc()}")
            return None
    
    def get_user_stats(self, username):
        """
        Get user statistics from Mikrotik router.
        
        Args:
            username (str): Username for the session
            
        Returns:
            dict: User statistics or None if error
        """
        try:
            with self.mikrotik_connection():
                # Get user information
                user_path = self.connection.path('/user')
                users = user_path.select().where(name=username)
                
                # Check if users exist
                users_list = list(users)
                if users_list:
                    user = users_list[0]  # Get the first user (should be only one)
                    return {
                        'username': user['name'],
                        'active': user.get('active', False),
                        'last_logged_in': user.get('last-logged-in', None),
                    }
                
                logger.warning(f"User {username} not found on Mikrotik router")
                return None
        except LibRouterosError as e:
            logger.error(f"Failed to get user stats for {username}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting user stats for {username}: {str(e)}\n{traceback.format_exc()}")
            return None
    
    def get_connected_devices(self):
        """
        Get all connected devices with their MAC addresses and IP addresses.
        
        Returns:
            list: List of connected devices with MAC addresses, IP addresses, and other details
        """
        try:
            with self.mikrotik_connection():
                # Get DHCP leases (active connections)
                dhcp_path = self.connection.path('/ip/dhcp-server/lease')
                leases = dhcp_path.select()
                
                # Get ARP table for additional device info
                arp_path = self.connection.path('/ip/arp')
                arp_entries = arp_path.select()
                
                # Get wireless registrations if wireless is enabled
                wireless_path = self.connection.path('/interface/wireless/registration-table')
                wireless_clients = []
                try:
                    wireless_clients = wireless_path.select()
                except Exception as e:
                    # Wireless might not be enabled, skip wireless clients
                    logger.debug(f"Wireless interface not available or enabled: {str(e)}")
                    pass
                
                devices = []
                
                # Process DHCP leases
                for lease in leases:
                    device = {
                        'mac_address': lease.get('mac-address', ''),
                        'ip_address': lease.get('address', ''),
                        'hostname': lease.get('host-name', 'Unknown'),
                        'status': lease.get('status', 'unknown'),
                        'expires_at': lease.get('expires-after', ''),
                        'client_id': lease.get('client-id', ''),
                        'server': lease.get('server', ''),
                        'active': lease.get('active', False),
                        'type': 'dhcp'
                    }
                    
                    # Find matching ARP entry for additional info
                    for arp in arp_entries:
                        if arp.get('mac-address') == device['mac_address']:
                            device['interface'] = arp.get('interface', '')
                            device['arp_status'] = arp.get('status', '')
                            break
                    
                    # Find matching wireless client
                    for client in wireless_clients:
                        if client.get('mac-address') == device['mac_address']:
                            device['wireless_info'] = {
                                'interface': client.get('interface', ''),
                                'uptime': client.get('uptime', ''),
                                'signal_strength': client.get('signal-strength', ''),
                                'tx_rate': client.get('tx-rate', ''),
                                'rx_rate': client.get('rx-rate', ''),
                                'ssid': client.get('ssid', '')
                            }
                            device['type'] = 'wireless'
                            break
                    
                    devices.append(device)
                
                # Also get active hotspot users if hotspot is enabled
                try:
                    hotspot_path = self.connection.path('/ip/hotspot/active')
                    hotspot_users = hotspot_path.select()
                    
                    for user in hotspot_users:
                        device = {
                            'mac_address': user.get('mac-address', ''),
                            'ip_address': user.get('address', ''),
                            'username': user.get('user', ''),
                            'uptime': user.get('uptime', ''),
                            'idle_time': user.get('idle-time', ''),
                            'bytes_in': user.get('bytes-in', 0),
                            'bytes_out': user.get('bytes-out', 0),
                            'type': 'hotspot'
                        }
                        devices.append(device)
                except Exception as e:
                    # Hotspot might not be enabled, skip hotspot users
                    logger.debug(f"Hotspot interface not available or enabled: {str(e)}")
                    pass
                
                logger.info(f"Retrieved {len(devices)} connected devices from Mikrotik")
                return devices
                
        except LibRouterosError as e:
            logger.error(f"Failed to get connected devices from Mikrotik: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting connected devices: {str(e)}\n{traceback.format_exc()}")
            return []
    
    def get_device_by_mac(self, mac_address):
        """
        Get specific device information by MAC address.
        
        Args:
            mac_address (str): MAC address to search for
            
        Returns:
            dict: Device information or None if not found
        """
        try:
            devices = self.get_connected_devices()
            
            for device in devices:
                if device['mac_address'].lower() == mac_address.lower():
                    return device
            
            logger.warning(f"Device with MAC address {mac_address} not found")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting device by MAC address {mac_address}: {str(e)}\n{traceback.format_exc()}")
            return None
    
    def get_devices_by_interface(self, interface_name):
        """
        Get all devices connected to a specific interface.
        
        Args:
            interface_name (str): Interface name (e.g., 'wlan1', 'ether2')
            
        Returns:
            list: List of devices connected to the specified interface
        """
        try:
            devices = self.get_connected_devices()
            
            interface_devices = []
            for device in devices:
                if device.get('interface') == interface_name:
                    interface_devices.append(device)
                elif 'wireless_info' in device and device['wireless_info'].get('interface') == interface_name:
                    interface_devices.append(device)
            
            return interface_devices
        except Exception as e:
            logger.error(f"Unexpected error getting devices by interface {interface_name}: {str(e)}\n{traceback.format_exc()}")
            return []

# Example usage:
# mikrotik_manager = MikrotikSessionManager(
#     host='192.168.88.1',
#     username='admin',
#     password='password'
# )
#
# # Create a session
# mikrotik_manager.create_session(
#     session_id=1,
#     username='customer1',
#     password='customerpass',
#     data_limit_mb=1000
# )
#
# # Update session data
# mikrotik_manager.update_session_data(
#     session_id=1,
#     username='customer1',
#     data_used_mb=500
# )
#
# # Terminate session
# mikrotik_manager.terminate_session(
#     session_id=1,
#     username='customer1'
# )