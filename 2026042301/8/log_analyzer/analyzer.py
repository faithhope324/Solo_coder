from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import statistics


class LogAnalyzer:
    def __init__(self):
        self.logs: List[Dict] = []
        self.errors: List[Dict] = []
        
    def add_logs(self, logs: List[Dict]):
        for log in logs:
            if 'error' in log:
                self.errors.append(log)
            else:
                self.logs.append(log)
    
    def get_total_requests(self) -> int:
        return len(self.logs)
    
    def get_failed_parse_count(self) -> int:
        return len(self.errors)
    
    def get_http_error_count(self) -> int:
        return len(self.get_4xx_requests()) + len(self.get_5xx_requests())
    
    def get_requests_by_status(self) -> Dict[str, int]:
        status_counter = Counter()
        for log in self.logs:
            status = str(log.get('status', 'unknown'))
            if status.startswith('2'):
                status_counter['2xx'] += 1
            elif status.startswith('3'):
                status_counter['3xx'] += 1
            elif status.startswith('4'):
                status_counter['4xx'] += 1
            elif status.startswith('5'):
                status_counter['5xx'] += 1
            else:
                status_counter['other'] += 1
        return dict(status_counter)
    
    def get_error_requests(self) -> List[Dict]:
        return [log for log in self.logs if log.get('status', 0) >= 400]
    
    def get_4xx_requests(self) -> List[Dict]:
        return [log for log in self.logs if 400 <= log.get('status', 0) < 500]
    
    def get_5xx_requests(self) -> List[Dict]:
        return [log for log in self.logs if log.get('status', 0) >= 500]
    
    def get_top_error_paths(self, limit: int = 10) -> List[Dict[str, Any]]:
        error_paths = Counter()
        for log in self.get_error_requests():
            path = log.get('path', 'unknown')
            error_paths[path] += 1
        
        return [
            {'path': path, 'count': count}
            for path, count in error_paths.most_common(limit)
        ]
    
    def get_requests_by_hour(self) -> Dict[int, int]:
        hour_counter = defaultdict(int)
        for log in self.logs:
            timestamp = log.get('timestamp')
            if timestamp:
                hour = timestamp.hour
                hour_counter[hour] += 1
        
        return dict(sorted(hour_counter.items()))
    
    def get_requests_by_day(self) -> Dict[str, int]:
        day_counter = defaultdict(int)
        for log in self.logs:
            timestamp = log.get('timestamp')
            if timestamp:
                day = timestamp.strftime('%Y-%m-%d')
                day_counter[day] += 1
        
        return dict(sorted(day_counter.items()))
    
    def get_requests_by_method(self) -> Dict[str, int]:
        method_counter = Counter()
        for log in self.logs:
            method = log.get('method', 'unknown')
            method_counter[method] += 1
        return dict(method_counter)
    
    def get_top_ips(self, limit: int = 10) -> List[Dict[str, Any]]:
        ip_counter = Counter()
        for log in self.logs:
            ip = log.get('ip', 'unknown')
            ip_counter[ip] += 1
        
        return [
            {'ip': ip, 'count': count}
            for ip, count in ip_counter.most_common(limit)
        ]
    
    def get_top_paths(self, limit: int = 10) -> List[Dict[str, Any]]:
        path_counter = Counter()
        for log in self.logs:
            path = log.get('path', 'unknown')
            path_counter[path] += 1
        
        return [
            {'path': path, 'count': count}
            for path, count in path_counter.most_common(limit)
        ]
    
    def get_response_time_stats(self) -> Optional[Dict[str, float]]:
        response_times = [
            log.get('response_time')
            for log in self.logs
            if log.get('response_time') is not None
        ]
        
        if not response_times:
            return None
        
        return {
            'min': min(response_times),
            'max': max(response_times),
            'avg': statistics.mean(response_times),
            'median': statistics.median(response_times),
            'count': len(response_times)
        }
    
    def _remove_tzinfo(self, dt: datetime) -> datetime:
        if dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt
    
    def get_time_range(self) -> Optional[Dict[str, datetime]]:
        timestamps = [
            self._remove_tzinfo(log.get('timestamp'))
            for log in self.logs
            if log.get('timestamp') is not None
        ]
        
        if not timestamps:
            return None
        
        return {
            'start': min(timestamps),
            'end': max(timestamps)
        }
    
    def get_summary(self) -> Dict[str, Any]:
        time_range = self.get_time_range()
        status_dist = self.get_requests_by_status()
        status_4xx = status_dist.get('4xx', 0)
        status_5xx = status_dist.get('5xx', 0)
        
        return {
            'total_requests': self.get_total_requests(),
            'failed_parse_count': self.get_failed_parse_count(),
            'http_error_count': self.get_http_error_count(),
            'status_distribution': status_dist,
            'method_distribution': self.get_requests_by_method(),
            '4xx_count': status_4xx,
            '5xx_count': status_5xx,
            'unique_ips': len(set(log.get('ip') for log in self.logs if log.get('ip'))),
            'top_ips': self.get_top_ips(5),
            'top_paths': self.get_top_paths(5),
            'top_error_paths': self.get_top_error_paths(5),
            'hourly_distribution': self.get_requests_by_hour(),
            'daily_distribution': self.get_requests_by_day(),
            'response_time_stats': self.get_response_time_stats(),
            'time_range': time_range
        }
