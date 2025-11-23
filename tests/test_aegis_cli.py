import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from io import StringIO
import readchar
import importlib.util

# Load aegis-cli.py as a module
spec = importlib.util.spec_from_file_location("aegis_cli", os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'aegis-cli.py')))
aegis_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aegis_cli)

from aegis_core import OTP, Entry # Corrected import


class TestAegisCliInteractive(unittest.TestCase):

    def test_search_as_you_type_single_match_reveal(self):
        with \
            patch.object(aegis_cli, 'read_and_decrypt_vault_file') as mock_decrypt_vault,\
            patch.object(aegis_cli, 'get_otps') as mock_get_otps,\
            patch('os.system') as mock_os_system,\
            patch('readchar.readkey') as mock_readkey,\
            patch('sys.stdout', new_callable=StringIO) as mock_stdout,\
            patch('getpass.getpass', return_value='dummy_password') as mock_getpass,\
            patch('builtins.input', return_value='dummy_password') as mock_input,\
            patch.object(aegis_cli, 'load_config', return_value={
                "last_opened_vault": None,\
                "last_vault_dir": None,\
                "default_color_mode": True
            }) as mock_load_config,\
            patch.object(aegis_cli, 'save_config') as mock_save_config,\
            patch('sys.argv', ['aegis-cli.py', '--vault-path', '/mock/vault/path.json']):
            # Mock vault data and OTPs
            mock_vault_data = MagicMock()
            entry1 = MagicMock(spec=Entry)
            entry1.name = "Test OTP 1"
            entry1.issuer = "Issuer A"
            entry1.groups = []
            entry1.note = ""
            entry1.uuid = "uuid1"

            entry2 = MagicMock(spec=Entry)
            entry2.name = "Another OTP"
            entry2.issuer = "Issuer B"
            entry2.groups = []
            entry2.note = ""
            entry2.uuid = "uuid2"
            mock_vault_data.db.entries = [entry1, entry2]
            mock_vault_data.db.groups = [] # No groups to mock for this test
            mock_decrypt_vault.return_value = mock_vault_data

            mock_get_otps.return_value = {
                "uuid1": MagicMock(spec=OTP, uuid="uuid1", name="Test OTP 1", issuer="Issuer A", secret="SECRET1", string=lambda: "SECRET1"),
                "uuid2": MagicMock(spec=OTP, uuid="uuid2", name="Another OTP", issuer="Issuer B", secret="SECRET2", string=lambda: "SECRET2"),
            }

            # Simulate user typing "Test" then Enter
            mock_readkey.side_effect = ['T', 'e', 's', 't', readchar.key.ENTER, readchar.key.CTRL_C]

            # Mock os.system('clear') to do nothing
            mock_os_system.return_value = None

            try:
                aegis_cli.main()
            except SystemExit:
                pass # argparse.parse_args() can call sys.exit()

            output = mock_stdout.getvalue()
            
            # Verify that "Test OTP 1" is revealed
            self.assertIn("Test OTP 1", output)
            self.assertIn("SECRET1", output)
            self.assertNotIn("SECRET2", output) # Ensure other OTPs are not revealed

    def test_search_as_you_type_no_match(self):
        with \
            patch.object(aegis_cli, 'read_and_decrypt_vault_file') as mock_decrypt_vault,\
            patch.object(aegis_cli, 'get_otps') as mock_get_otps,\
            patch('os.system') as mock_os_system,\
            patch('readchar.readkey') as mock_readkey,\
            patch('sys.stdout', new_callable=StringIO) as mock_stdout,\
            patch('getpass.getpass', return_value='dummy_password') as mock_getpass,\
            patch('builtins.input', return_value='dummy_password') as mock_input,\
            patch.object(aegis_cli, 'load_config', return_value={
                "last_opened_vault": None,\
                "last_vault_dir": None,\
                "default_color_mode": True
            }) as mock_load_config,\
            patch.object(aegis_cli, 'save_config') as mock_save_config,\
            patch('sys.argv', ['aegis-cli.py', '--vault-path', '/mock/vault/path.json']):
            # Mock vault data and OTPs
            mock_vault_data = MagicMock()
            entry1 = MagicMock(spec=Entry)
            entry1.name = "Test OTP 1"
            entry1.issuer = "Issuer A"
            entry1.groups = []
            entry1.note = ""
            entry1.uuid = "uuid1"
            mock_vault_data.db.entries = [entry1]
            mock_vault_data.db.groups = []
            mock_decrypt_vault.return_value = mock_vault_data

            mock_get_otps.return_value = {
                "uuid1": MagicMock(spec=OTP, uuid="uuid1", name="Test OTP 1", issuer="Issuer A", secret="SECRET1", string=lambda: "SECRET1"),
            }

            # Simulate user typing "Nomatch" then Ctrl+C
            mock_readkey.side_effect = ['N', 'o', 'm', 'a', 't', 'c', 'h', readchar.key.CTRL_C]

            # Mock os.system('clear') to do nothing
            mock_os_system.return_value = None

            try:
                aegis_cli.main()
            except SystemExit:
                pass

            output = mock_stdout.getvalue()
            
            # Split output by the prompt to get the final display state
            prompt_string_prefix = "Type the name or line number to reveal OTP code (Ctrl+C to exit): "
            output_segments = output.split(prompt_string_prefix)
            
            # The last segment should contain the final display before exit
            final_display_segment = output_segments[-1]

            # Verify that no OTPs are displayed and the search term is present in the prompt
            self.assertIn("Nomatch", final_display_segment) # Ensure the search term is in the last prompt
            self.assertNotIn("Test OTP 1", final_display_segment)
            self.assertNotIn("SECRET1", final_display_segment)


    def test_search_as_you_type_multiple_matches_no_reveal(self):
        with \
            patch.object(aegis_cli, 'read_and_decrypt_vault_file') as mock_decrypt_vault,\
            patch.object(aegis_cli, 'get_otps') as mock_get_otps,\
            patch('os.system') as mock_os_system,\
            patch('readchar.readkey') as mock_readkey,\
            patch('sys.stdout', new_callable=StringIO) as mock_stdout,\
            patch('getpass.getpass', return_value='dummy_password') as mock_getpass,\
            patch('builtins.input', return_value='dummy_password') as mock_input,\
            patch.object(aegis_cli, 'load_config', return_value={
                "last_opened_vault": None,\
                "last_vault_dir": None,\
                "default_color_mode": True
            }) as mock_load_config,\
            patch.object(aegis_cli, 'save_config') as mock_save_config,\
            patch('sys.argv', ['aegis-cli.py', '--vault-path', '/mock/vault/path.json']):
            # Mock vault data and OTPs
            mock_vault_data = MagicMock()
            entry1 = MagicMock(spec=Entry)
            entry1.name = "Test OTP 1"
            entry1.issuer = "Issuer A"
            entry1.groups = []
            entry1.note = ""
            entry1.uuid = "uuid1"

            entry2 = MagicMock(spec=Entry)
            entry2.name = "Test OTP 2"
            entry2.issuer = "Issuer B"
            entry2.groups = []
            entry2.note = ""
            entry2.uuid = "uuid2"
            mock_vault_data.db.entries = [entry1, entry2]
            mock_vault_data.db.groups = []
            mock_decrypt_vault.return_value = mock_vault_data

            mock_get_otps.return_value = {
                "uuid1": MagicMock(spec=OTP, uuid="uuid1", name="Test OTP 1", issuer="Issuer A", secret="SECRET1", string=lambda: "SECRET1"),
                "uuid2": MagicMock(spec=OTP, uuid="uuid2", name="Test OTP 2", issuer="Issuer B", secret="SECRET2", string=lambda: "SECRET2"),
            }

            # Simulate user typing "Test" then Ctrl+C
            mock_readkey.side_effect = ['T', 'e', 's', 't', readchar.key.CTRL_C]

            # Mock os.system('clear') to do nothing
            mock_os_system.return_value = None

            try:
                aegis_cli.main()
            except SystemExit:
                pass

            output = mock_stdout.getvalue()
            
            # Verify that both OTPs are listed but not revealed
            self.assertIn("Test OTP 1", output)
            self.assertIn("Test OTP 2", output)
            self.assertNotIn("SECRET1", output)
            self.assertNotIn("SECRET2", output)
            self.assertIn("******", output) # Should see obscured OTPs

if __name__ == '__main__':
    unittest.main()
