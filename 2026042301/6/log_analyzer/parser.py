import re
from datetime import datetime
from typing import List, Dict, Optional, Iterator


class LogParser:
    def __init__(self):
        self.nginx_pattern = re.compile(
            r'(\S+) - (\S+) \[(.*?)\] '
            r'"(\S+) (\S+) (\S+)" '
            r'(\d+) (\d+) '
            r'"(.*?)" "(.*?)"'
        )
        
        self.apache_pattern = re.compile(
            r'(\S+) (\S+) (\S+) \[(.*?)\] '
            r'"(\S+) (\S+) (\S+)" '
            r'(\d+) (\d+)'
        )
        
        self.custom_pattern = re.compile(
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?) '
            r'(\S+) (\S+) (\d+) (\S+) '
            r'"(\S+) (\S+)" '
            r'"?(\d+)"? "?(\d+)ms"?'
        )

    def parse_nginx_log(self, line: str) -> Optional[Dict]:
        match = self.nginx_pattern.match(line)
        if match:
            return {
                'ip': match.group(1),
                'user': match.group(2),
                'timestamp': self._parse_timestamp(match.group(3)),
                'method': match.group(4),
                'path': match.group(5),
                'protocol': match.group(6),
                'status': int(match.group(7)),
                'size': int(match.group(8)),
                'referrer': match.group(9),
                'user_agent': match.group(10),
                'raw': line
            }
        return None

    def parse_apache_log(self, line: str) -> Optional[Dict]:
        match = self.apache_pattern.match(line)
        if match:
            return {
                'ip': match.group(1),
                'remote_logname': match.group(2),
                'user': match.group(3),
                'timestamp': self._parse_timestamp(match.group(4)),
                'method': match.group(5),
                'path': match.group(6),
                'protocol': match.group(7),
                'status': int(match.group(8)),
                'size': int(match.group(9)) if match.group(9) != '-' else 0,
                'raw': line
            }
        return None

    def parse_custom_log(self, line: str) -> Optional[Dict]:
        match = self.custom_pattern.search(line)
        if match:
            timestamp = self._parse_timestamp(match.group(1))
            if timestamp is None:
                return None
            return {
                'timestamp': timestamp,
                'log_level': match.group(2),
                'service': match.group(3),
                'process_id': int(match.group(4)),
                'ip': match.group(5),
                'method': match.group(6),
                'path': match.group(7),
                'status': int(match.group(8)),
                'response_time': int(match.group(9)),
                'raw': line
            }
        return None

    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        timestamp_str = timestamp_str.strip()
        
        formats = [
            '%d/%b/%Y:%H:%M:%S %z',
            '%d/%b/%Y:%H:%M:%S',
            '%Y-%m-%d %H:%M:%S %z',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f %z',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y/%m/%d %H:%M:%S %z',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d %H:%M:%S.%f %z',
            '%Y/%m/%d %H:%M:%S.%f',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        
        import re
        date_match = re.search(
            r'(\d{4}[-/]\d{2}[-/]\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?)(?:\s+[+-]\d{4})?',
            timestamp_str
        )
        if date_match:
            extracted = date_match.group(1)
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', 
                       '%Y/%m/%d %H:%M:%S', '%Y/%m/%d %H:%M:%S.%f']:
                try:
                    return datetime.strptime(extracted, fmt)
                except ValueError:
                    continue
        
        return None

    def parse_line(self, line: str) -> Optional[Dict]:
        parsers = [
            self.parse_nginx_log,
            self.parse_apache_log,
            self.parse_custom_log
        ]
        
        for parser in parsers:
            result = parser(line)
            if result:
                return result
        return None

    def parse_file(self, file_path: str) -> Iterator[Dict]:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                parsed = self.parse_line(line)
                if parsed:
                    parsed['line_num'] = line_num
                    yield parsed
                else:
                    yield {
                        'line_num': line_num,
                        'raw': line,
                        'error': 'Failed to parse'
                    }

    def parse_file_list(self, file_paths: List[str]) -> Iterator[Dict]:
        for file_path in file_paths:
            yield from self.parse_file(file_path)
