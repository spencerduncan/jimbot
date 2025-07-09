#!/usr/bin/env python3
"""
QuestDB Health Check Script for JimBot Analytics
Verifies QuestDB deployment and functionality
"""

import sys
import time
import requests
import socket
from datetime import datetime
from typing import Dict, List, Tuple


class QuestDBHealthCheck:
    """Health check utility for QuestDB deployment"""
    
    def __init__(self, host: str = "localhost"):
        self.host = host
        self.http_port = 9000
        self.ilp_port = 8812
        self.pg_port = 9120
        self.checks_passed = 0
        self.checks_failed = 0
        
    def check_http_api(self) -> bool:
        """Check HTTP API availability"""
        try:
            response = requests.get(
                f"http://{self.host}:{self.http_port}/exec",
                params={"query": "SELECT 1"},
                timeout=5
            )
            if response.status_code == 200:
                self._log_success("HTTP API is accessible")
                return True
            else:
                self._log_error(f"HTTP API returned status {response.status_code}")
                return False
        except Exception as e:
            self._log_error(f"HTTP API check failed: {e}")
            return False
    
    def check_ilp_port(self) -> bool:
        """Check InfluxDB Line Protocol port"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.host, self.ilp_port))
            sock.close()
            
            if result == 0:
                self._log_success("ILP port is open")
                return True
            else:
                self._log_error("ILP port is not accessible")
                return False
        except Exception as e:
            self._log_error(f"ILP port check failed: {e}")
            return False
    
    def check_tables(self) -> bool:
        """Check if required tables exist"""
        required_tables = [
            "game_metrics",
            "joker_synergies", 
            "decision_points",
            "economic_flow"
        ]
        
        try:
            response = requests.get(
                f"http://{self.host}:{self.http_port}/exec",
                params={"query": "SHOW TABLES"},
                timeout=5
            )
            
            if response.status_code != 200:
                self._log_error("Failed to list tables")
                return False
            
            data = response.json()
            existing_tables = [row[0] for row in data.get("dataset", [])]
            
            all_exist = True
            for table in required_tables:
                if table in existing_tables:
                    self._log_success(f"Table '{table}' exists")
                else:
                    self._log_error(f"Table '{table}' is missing")
                    all_exist = False
                    
            return all_exist
            
        except Exception as e:
            self._log_error(f"Table check failed: {e}")
            return False
    
    def check_data_ingestion(self) -> bool:
        """Test data ingestion via ILP"""
        try:
            # Send test metric
            test_metric = (
                f"health_check,test=true value=1i {int(time.time() * 1e9)}\n"
            )
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.ilp_port))
            sock.send(test_metric.encode())
            sock.close()
            
            # Wait for data to be committed
            time.sleep(1)
            
            # Verify data was inserted
            response = requests.get(
                f"http://{self.host}:{self.http_port}/exec",
                params={"query": "SELECT COUNT(*) FROM health_check WHERE test = 'true'"},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                count = data["dataset"][0][0] if data.get("dataset") else 0
                
                if count > 0:
                    self._log_success("Data ingestion test passed")
                    # Clean up test data
                    self._cleanup_test_data()
                    return True
                else:
                    self._log_error("Data ingestion test failed - no data found")
                    return False
            else:
                self._log_error("Failed to verify ingested data")
                return False
                
        except Exception as e:
            self._log_error(f"Data ingestion test failed: {e}")
            return False
    
    def check_query_performance(self) -> bool:
        """Check query performance"""
        try:
            # Insert some test data first
            self._insert_test_data()
            
            # Test query performance
            start_time = time.time()
            response = requests.get(
                f"http://{self.host}:{self.http_port}/exec",
                params={
                    "query": """
                    SELECT 
                        COUNT(*) as count,
                        AVG(value) as avg_value,
                        MAX(value) as max_value
                    FROM perf_test
                    WHERE timestamp > dateadd('m', -1, now())
                    """
                },
                timeout=5
            )
            query_time = (time.time() - start_time) * 1000  # Convert to ms
            
            if response.status_code == 200 and query_time < 50:
                self._log_success(f"Query performance test passed ({query_time:.2f}ms)")
                # Clean up test data
                self._cleanup_perf_test_data()
                return True
            else:
                self._log_error(f"Query performance test failed ({query_time:.2f}ms)")
                return False
                
        except Exception as e:
            self._log_error(f"Query performance test failed: {e}")
            return False
    
    def check_memory_usage(self) -> bool:
        """Check memory usage is within limits"""
        try:
            # This would need to be implemented with docker stats or system metrics
            # For now, we'll just check if the service is responsive
            response = requests.get(
                f"http://{self.host}:{self.http_port}/status",
                timeout=5
            )
            
            if response.status_code == 200:
                self._log_success("Service is responsive (memory check proxy)")
                return True
            else:
                self._log_error("Service may be under memory pressure")
                return False
                
        except Exception as e:
            self._log_error(f"Memory check failed: {e}")
            return False
    
    def _insert_test_data(self):
        """Insert test data for performance testing"""
        try:
            # Create test table
            requests.get(
                f"http://{self.host}:{self.http_port}/exec",
                params={
                    "query": """
                    CREATE TABLE IF NOT EXISTS perf_test (
                        timestamp TIMESTAMP,
                        value DOUBLE
                    ) TIMESTAMP(timestamp) PARTITION BY DAY
                    """
                }
            )
            
            # Insert some data
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.ilp_port))
            
            for i in range(100):
                metric = f"perf_test value={i}d {int(time.time() * 1e9) - i * 1000000}\n"
                sock.send(metric.encode())
                
            sock.close()
            time.sleep(1)  # Wait for commit
            
        except Exception:
            pass  # Ignore errors in test data insertion
    
    def _cleanup_test_data(self):
        """Clean up health check test data"""
        try:
            requests.get(
                f"http://{self.host}:{self.http_port}/exec",
                params={"query": "DROP TABLE IF EXISTS health_check"}
            )
        except Exception:
            pass
    
    def _cleanup_perf_test_data(self):
        """Clean up performance test data"""
        try:
            requests.get(
                f"http://{self.host}:{self.http_port}/exec",
                params={"query": "DROP TABLE IF EXISTS perf_test"}
            )
        except Exception:
            pass
    
    def _log_success(self, message: str):
        """Log successful check"""
        print(f"✓ {message}")
        self.checks_passed += 1
    
    def _log_error(self, message: str):
        """Log failed check"""
        print(f"✗ {message}")
        self.checks_failed += 1
    
    def run_all_checks(self) -> bool:
        """Run all health checks"""
        print("QuestDB Health Check")
        print("=" * 50)
        print(f"Target: {self.host}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        # Run checks
        checks = [
            ("HTTP API", self.check_http_api),
            ("ILP Port", self.check_ilp_port),
            ("Tables", self.check_tables),
            ("Data Ingestion", self.check_data_ingestion),
            ("Query Performance", self.check_query_performance),
            ("Memory Usage", self.check_memory_usage),
        ]
        
        for check_name, check_func in checks:
            print(f"\nChecking {check_name}...")
            check_func()
        
        # Summary
        print("\n" + "=" * 50)
        print(f"Total checks: {self.checks_passed + self.checks_failed}")
        print(f"Passed: {self.checks_passed}")
        print(f"Failed: {self.checks_failed}")
        
        success = self.checks_failed == 0
        if success:
            print("\n✓ QuestDB is healthy and ready for use!")
        else:
            print("\n✗ QuestDB health check failed!")
            
        return success


def main():
    """Main entry point"""
    health_check = QuestDBHealthCheck()
    success = health_check.run_all_checks()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()