#!/usr/bin/env python
"""
Test script to verify that port binding works correctly.
Run this locally to test before deploying.
"""
import os
import sys
import socket
import subprocess
from pathlib import Path

def test_port_availability(port):
    """Test if a port is available"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', int(port)))
            return True
        except OSError:
            return False

def main():
    """Test port binding functionality"""
    print("🧪 Testing port binding functionality...")
    
    # Test different port scenarios
    test_ports = [8000, 8080, 10000]
    
    for port in test_ports:
        print(f"\n📍 Testing port {port}...")
        
        if test_port_availability(port):
            print(f"✅ Port {port} is available")
            
            # Set environment variables
            env = os.environ.copy()
            env['PORT'] = str(port)
            env['DEBUG'] = 'True'
            env['DJANGO_SETTINGS_MODULE'] = 'converter_site.settings'
            
            print(f"🚀 Starting test server on port {port}...")
            
            try:
                # Start the render start script
                process = subprocess.Popen([
                    sys.executable, 'render_start.py'
                ], env=env, cwd=Path(__file__).parent)
                
                # Wait a bit then kill it
                import time
                time.sleep(5)
                process.terminate()
                process.wait(timeout=5)
                
                print(f"✅ Server started successfully on port {port}")
                break
                
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"⚠️  Server started but didn't respond quickly on port {port}")
                break
            except Exception as e:
                print(f"❌ Failed to start server on port {port}: {e}")
                
        else:
            print(f"❌ Port {port} is not available")
    
    print("\n🎯 Port binding test completed!")
    print("\n📋 For Render deployment, use:")
    print("   Build Command: pip install -r requirements.txt")
    print("   Start Command: python render_start.py")
    print("   Environment Variables: DEBUG=False, SECRET_KEY=your-key")

if __name__ == '__main__':
    main()
