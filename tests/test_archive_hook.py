"""Exercise the generation-to-archive hook against an isolated HTTP receiver."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from argparse import Namespace
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

class HookTests(unittest.TestCase):
    def test_hook(self):
        received = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                self.send_response(200); self.end_headers()
                self.wfile.write(b'{"schema_version":1}')
            def do_POST(self):
                received.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(200); self.end_headers()
                self.wfile.write(b'{"ok":true,"student_id":"example","material_ids":["file"]}')
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with tempfile.TemporaryDirectory() as folder:
                work = Path(folder)
                token = work / 'token'; token.write_text('test-only')
                with patch.dict(os.environ, {'WENYUAN_WORKBENCH_URL': f'http://127.0.0.1:{server.server_port}', 'WENYUAN_WORKBENCH_TOKEN_FILE': str(token)}):
                    import run
                    (work/'draft.json').write_text(json.dumps({'student':'示例学生','subject':'数学','questions':[]},ensure_ascii=False),encoding='utf-8')
                    (work/'report.pdf').write_bytes(b'%PDF-test')
                    args = Namespace(work=str(work),format='final',docx=False,python=None,student_id=None,archive_manifest=work/'result.archive.json')
                    with patch.object(run,'cmd_check',return_value=0), patch.object(run,'cmd_digest',return_value=0), patch.object(run,'cmd_render',return_value=0):
                        self.assertEqual(run.cmd_finish(args),0)
                    self.assertEqual(received[0]['type'],'exam-analysis')
                    with patch.object(run,'cmd_check',return_value=2):
                        self.assertEqual(run.cmd_finish(args),2)
                    self.assertEqual(len(received),1)
        finally:
            server.shutdown(); server.server_close(); thread.join()

if __name__ == '__main__': unittest.main()
