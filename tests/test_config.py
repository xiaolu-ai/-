# -*- coding: utf-8 -*-
"""
配置管理器单元测试
测试配置加载、保存、默认配置生成和错误处理功能
"""

import unittest
import json
import tempfile
import os
from pathlib import Path
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import ConfigManager


class TestConfigManager(unittest.TestCase):
    """配置管理器测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时目录用于测试
        self.temp_dir = tempfile.mkdtemp()
        self.test_config_file = Path(self.temp_dir) / "test_config.json"
        
    def tearDown(self):
        """测试后清理"""
        # 清理临时文件
        if self.test_config_file.exists():
            self.test_config_file.unlink()
        
        # 清理临时目录
        try:
            os.rmdir(self.temp_dir)
        except OSError:
            pass
    
    def test_default_config_generation(self):
        """测试默认配置生成"""
        config = ConfigManager(str(self.test_config_file))
        default_config = config.get_default_config()
        
        # 验证默认配置包含所有必要的键
        self.assertIn("screenshot", default_config)
        self.assertIn("player", default_config)
        self.assertIn("annotation", default_config)
        self.assertIn("ui", default_config)
        
        # 验证截图配置
        screenshot_config = default_config["screenshot"]
        self.assertIn("save_directory", screenshot_config)
        self.assertIn("batch_interval", screenshot_config)
        self.assertIn("auto_annotation", screenshot_config)
        self.assertIn("font_size", screenshot_config)
        self.assertIn("font_color", screenshot_config)
        
        # 验证播放器配置
        player_config = default_config["player"]
        self.assertIn("default_volume", player_config)
        self.assertIn("remember_position", player_config)
        self.assertIn("default_playback_rate", player_config)
        
        # 验证标注配置
        annotation_config = default_config["annotation"]
        self.assertIn("default_color", annotation_config)
        self.assertIn("line_width", annotation_config)
        self.assertIn("arrow_size", annotation_config)
        
        # 验证UI配置
        ui_config = default_config["ui"]
        self.assertIn("window_geometry", ui_config)
        self.assertIn("last_video_directory", ui_config)
    
    def test_config_file_creation(self):
        """测试配置文件创建"""
        # 确保配置文件不存在
        self.assertFalse(self.test_config_file.exists())
        
        # 创建配置管理器，应该自动创建配置文件
        config = ConfigManager(str(self.test_config_file))
        
        # 验证配置文件已创建
        self.assertTrue(self.test_config_file.exists())
        
        # 验证文件内容是有效的JSON
        with open(self.test_config_file, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
            self.assertIsInstance(loaded_data, dict)
    
    def test_config_loading(self):
        """测试配置加载"""
        # 创建测试配置数据
        test_config = {
            "test_section": {
                "test_key": "test_value",
                "test_number": 42
            }
        }
        
        # 手动写入配置文件
        with open(self.test_config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f, indent=4)
        
        # 创建配置管理器并加载
        config = ConfigManager(str(self.test_config_file))
        
        # 验证配置已正确加载
        self.assertEqual(config.get("test_section.test_key"), "test_value")
        self.assertEqual(config.get("test_section.test_number"), 42)
    
    def test_config_saving(self):
        """测试配置保存"""
        config = ConfigManager(str(self.test_config_file))
        
        # 修改配置
        test_data = {"new_section": {"new_key": "new_value"}}
        config.save_config(test_data)
        
        # 验证文件已更新
        with open(self.test_config_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
            self.assertEqual(saved_data["new_section"]["new_key"], "new_value")
    
    def test_get_method(self):
        """测试配置项获取方法"""
        config = ConfigManager(str(self.test_config_file))
        
        # 测试获取存在的配置项
        volume = config.get("player.default_volume")
        self.assertEqual(volume, 80)
        
        # 测试获取不存在的配置项（返回默认值）
        non_existent = config.get("non.existent.key", "default")
        self.assertEqual(non_existent, "default")
        
        # 测试获取不存在的配置项（返回None）
        none_value = config.get("another.non.existent.key")
        self.assertIsNone(none_value)
    
    def test_set_method(self):
        """测试配置项设置方法"""
        config = ConfigManager(str(self.test_config_file))
        
        # 设置新的配置项
        config.set("test.new_key", "new_value")
        self.assertEqual(config.get("test.new_key"), "new_value")
        
        # 设置嵌套配置项
        config.set("deep.nested.key", 123)
        self.assertEqual(config.get("deep.nested.key"), 123)
        
        # 修改现有配置项
        config.set("player.default_volume", 90)
        self.assertEqual(config.get("player.default_volume"), 90)
    
    def test_update_config_method(self):
        """测试批量配置更新方法"""
        config = ConfigManager(str(self.test_config_file))
        
        # 准备更新数据
        updates = {
            "player": {
                "default_volume": 75,
                "new_setting": True
            },
            "new_section": {
                "key1": "value1",
                "key2": 42
            }
        }
        
        # 执行批量更新
        config.update_config(updates)
        
        # 验证更新结果
        self.assertEqual(config.get("player.default_volume"), 75)
        self.assertEqual(config.get("player.new_setting"), True)
        self.assertEqual(config.get("new_section.key1"), "value1")
        self.assertEqual(config.get("new_section.key2"), 42)
        
        # 验证原有配置项未被删除
        self.assertEqual(config.get("player.remember_position"), True)
    
    def test_corrupted_config_handling(self):
        """测试损坏配置文件的处理"""
        # 创建损坏的JSON文件
        with open(self.test_config_file, 'w', encoding='utf-8') as f:
            f.write("{ invalid json content")
        
        # 创建配置管理器，应该使用默认配置
        config = ConfigManager(str(self.test_config_file))
        
        # 验证使用了默认配置
        self.assertEqual(config.get("player.default_volume"), 80)
        
        # 验证文件已被修复（重新写入有效JSON）
        with open(self.test_config_file, 'r', encoding='utf-8') as f:
            repaired_data = json.load(f)
            self.assertIsInstance(repaired_data, dict)
    
    def test_missing_config_sections(self):
        """测试缺失配置节的处理"""
        # 创建不完整的配置文件
        incomplete_config = {
            "player": {
                "default_volume": 60
            }
            # 缺少其他配置节
        }
        
        with open(self.test_config_file, 'w', encoding='utf-8') as f:
            json.dump(incomplete_config, f)
        
        # 创建配置管理器
        config = ConfigManager(str(self.test_config_file))
        
        # 验证可以获取存在的配置
        self.assertEqual(config.get("player.default_volume"), 60)
        
        # 验证缺失的配置返回默认值
        self.assertIsNone(config.get("screenshot.save_directory"))
    
    def test_config_persistence(self):
        """测试配置持久化"""
        # 第一个配置管理器实例
        config1 = ConfigManager(str(self.test_config_file))
        config1.set("test.persistence", "persistent_value")
        config1.save_config()
        
        # 第二个配置管理器实例（模拟应用重启）
        config2 = ConfigManager(str(self.test_config_file))
        
        # 验证配置已持久化
        self.assertEqual(config2.get("test.persistence"), "persistent_value")
    
    def test_nested_config_operations(self):
        """测试嵌套配置操作"""
        config = ConfigManager(str(self.test_config_file))
        
        # 测试深层嵌套设置
        config.set("level1.level2.level3.deep_key", "deep_value")
        self.assertEqual(config.get("level1.level2.level3.deep_key"), "deep_value")
        
        # 测试中间层访问
        config.set("level1.level2.another_key", "another_value")
        self.assertEqual(config.get("level1.level2.another_key"), "another_value")
        
        # 验证深层嵌套仍然存在
        self.assertEqual(config.get("level1.level2.level3.deep_key"), "deep_value")


class TestConfigManagerIntegration(unittest.TestCase):
    """配置管理器集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_config_file = Path(self.temp_dir) / "integration_test.json"
    
    def tearDown(self):
        """测试后清理"""
        if self.test_config_file.exists():
            self.test_config_file.unlink()
        try:
            os.rmdir(self.temp_dir)
        except OSError:
            pass
    
    def test_real_world_usage_scenario(self):
        """测试真实使用场景"""
        # 模拟应用首次启动
        config = ConfigManager(str(self.test_config_file))
        
        # 用户修改截图设置
        config.set("screenshot.save_directory", "/custom/path")
        config.set("screenshot.batch_interval", 10)
        config.set("screenshot.font_size", 20)
        
        # 用户修改播放器设置
        config.set("player.default_volume", 65)
        config.set("player.default_playback_rate", 1.25)
        
        # 用户修改窗口位置
        config.set("ui.window_geometry", [200, 150, 1400, 900])
        
        # 保存配置
        config.save_config()
        
        # 模拟应用重启
        config2 = ConfigManager(str(self.test_config_file))
        
        # 验证所有设置都已保存
        self.assertEqual(config2.get("screenshot.save_directory"), "/custom/path")
        self.assertEqual(config2.get("screenshot.batch_interval"), 10)
        self.assertEqual(config2.get("screenshot.font_size"), 20)
        self.assertEqual(config2.get("player.default_volume"), 65)
        self.assertEqual(config2.get("player.default_playback_rate"), 1.25)
        self.assertEqual(config2.get("ui.window_geometry"), [200, 150, 1400, 900])
        
        # 验证未修改的设置保持默认值
        self.assertEqual(config2.get("annotation.default_color"), "#FF0000")
        self.assertEqual(config2.get("annotation.line_width"), 3)


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_suite.addTests(loader.loadTestsFromTestCase(TestConfigManager))
    test_suite.addTests(loader.loadTestsFromTestCase(TestConfigManagerIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("=" * 60)
    print("配置管理器单元测试")
    print("=" * 60)
    
    success = run_tests()
    
    if success:
        print("\n🎉 所有测试通过！配置管理器功能正常！")
    else:
        print("\n❌ 部分测试失败，请检查配置管理器实现")
    
    exit(0 if success else 1)