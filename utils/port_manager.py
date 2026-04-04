# -*- coding: utf-8 -*-
"""
Port Manager - 端口管理工具
提供端口清理和进程管理功能
"""

import subprocess
import logging
import time
import platform
from typing import List, Optional

logger = logging.getLogger(__name__)


class PortManager:
    """端口管理器"""

    @staticmethod
    def kill_port(port: int, timeout: int = 5) -> bool:
        """
        终止占用指定端口的进程（Windows）
        
        Args:
            port: 端口号
            timeout: 超时时间（秒）
            
        Returns:
            是否成功终止
        """
        try:
            result = subprocess.run(
                f'netstat -ano | findstr ":{port} "',
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            lines = result.stdout.strip().split('\n')
            pids = set()
            
            for line in lines:
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        pid = int(parts[-1])
                        if pid > 0:
                            pids.add(pid)
                    except ValueError:
                        continue
            
            if not pids:
                logger.info(f"端口 {port} 未被占用")
                return True
            
            for pid in pids:
                subprocess.run(
                    f'taskkill /F /PID {pid}',
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                logger.info(f"已终止进程 PID: {pid}")
            
            logger.info(f"已清理端口 {port}")
            return True
            
        except subprocess.TimeoutExpired:
            logger.warning(f"端口 {port} 清理超时")
            return False
        except Exception as e:
            logger.error(f"清理端口 {port} 失败: {e}")
            return False

    @staticmethod
    def kill_port_force(port: int) -> bool:
        """
        强制清理端口，重试机制确保成功
        
        Args:
            port: 端口号
            
        Returns:
            是否成功终止
        """
        max_retries = 3
        for attempt in range(max_retries):
            if not PortManager.is_port_in_use(port):
                logger.info(f"端口 {port} 已空闲")
                return True
            
            logger.info(f"尝试清理端口 {port} (第 {attempt + 1} 次)")
            PortManager.kill_port(port)
            time.sleep(1)
        
        if PortManager.is_port_in_use(port):
            logger.warning(f"端口 {port} 清理失败，强制重试")
            time.sleep(2)
            PortManager.kill_port(port)
            time.sleep(1)
        
        return not PortManager.is_port_in_use(port)

    @staticmethod
    def is_port_in_use(port: int) -> bool:
        """检查端口是否被占用"""
        try:
            result = subprocess.run(
                f'netstat -ano | findstr ":{port} "',
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

    @staticmethod
    def kill_ports(ports: List[int]) -> dict:
        """终止占用多个端口的进程"""
        result = {"success": [], "failed": []}
        for port in ports:
            if PortManager.kill_port_force(port):
                result["success"].append(port)
            else:
                result["failed"].append(port)
        return result

    @staticmethod
    def wait_for_port_free(port: int, timeout: int = 10) -> bool:
        """等待端口释放"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not PortManager.is_port_in_use(port):
                return True
            time.sleep(0.5)
        return False

    @staticmethod
    def get_port_process(port: int) -> Optional[dict]:
        """获取占用端口的进程信息"""
        try:
            result = subprocess.run(
                f'netstat -ano | findstr ":{port} "',
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                if lines:
                    parts = lines[0].split()
                    if len(parts) >= 5:
                        return {"pid": int(parts[-1]), "state": parts[3] if len(parts) > 3 else "unknown"}
        except Exception as e:
            logger.error(f"获取端口 {port} 进程信息失败: {e}")
        return None


def kill_port_and_wait(port: int, wait_seconds: int = 2) -> bool:
    """终止端口进程并等待释放"""
    PortManager.kill_port_force(port)
    time.sleep(wait_seconds)
    return not PortManager.is_port_in_use(port)
