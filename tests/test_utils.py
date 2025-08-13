# -*- coding: utf-8 -*-
"""
工具函数单元测试
测试时间格式化、文件管理和图像处理工具函数
"""

import unittest
import tempfile
import os
from pathlib import Path
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils import TimeFormatter, FileManager, ImageProcessor


class TestTimeFormatter(unittest.TestCase):
    """时间格式化工具测试类"""
    
    def test_ms_to_time_string(self):
        """测试毫秒转时间字符串"""
        # 测试基本转换
        self.assertEqual(TimeFormatter.ms_to_time_string(0), "00:00:00")
        self.assertEqual(TimeFormatter.ms_to_time_string(1000), "00:00:01")
        self.assertEqual(TimeFormatter.ms_to_time_string(60000), "00:01:00")
        self.assertEqual(TimeFormatter.ms_to_time_string(3600000), "01:00:00")
        
        # 测试复合时间
        self.assertEqual(TimeFormatter.ms_to_time_string(3661000), "01:01:01")
        self.assertEqual(TimeFormatter.ms_to_time_string(125000), "00:02:05")
        
        # 测试负数处理
        self.assertEqual(TimeFormatter.ms_to_time_string(-1000), "00:00:00")
        
        # 测试大数值
        self.assertEqual(TimeFormatter.ms_to_time_string(7323000), "02:02:03")
    
    def test_time_string_to_ms(self):
        """测试时间字符串转毫秒"""
        # 测试 HH:MM:SS 格式
        self.assertEqual(TimeFormatter.time_string_to_ms("00:00:00"), 0)
        self.assertEqual(TimeFormatter.time_string_to_ms("00:00:01"), 1000)
        self.assertEqual(TimeFormatter.time_string_to_ms("00:01:00"), 60000)
        self.assertEqual(TimeFormatter.time_string_to_ms("01:00:00"), 3600000)
        self.assertEqual(TimeFormatter.time_string_to_ms("01:01:01"), 3661000)
        
        # 测试 MM:SS 格式
        self.assertEqual(TimeFormatter.time_string_to_ms("02:05"), 125000)
        self.assertEqual(TimeFormatter.time_string_to_ms("10:30"), 630000)
        
        # 测试错误格式
        self.assertEqual(TimeFormatter.time_string_to_ms("invalid"), 0)
        self.assertEqual(TimeFormatter.time_string_to_ms("1:2:3:4"), 0)
        self.assertEqual(TimeFormatter.time_string_to_ms(""), 0)
    
    def test_get_current_timestamp(self):
        """测试获取当前时间戳"""
        timestamp = TimeFormatter.get_current_timestamp()
        
        # 验证格式：YYYY-MM-DD_HH-MM-SS
        self.assertRegex(timestamp, r'^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$')
        
        # 验证长度
        self.assertEqual(len(timestamp), 19)


class TestFileManager(unittest.TestCase):
    """文件管理工具测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试后清理"""
        try:
            os.rmdir(self.temp_dir)
        except OSError:
            pass
    
    def test_ensure_directory_exists(self):
        """测试确保目录存在"""
        test_dir = Path(self.temp_dir) / "test_subdir"
        
        # 目录不存在时
        self.assertFalse(test_dir.exists())
        result = FileManager.ensure_directory_exists(str(test_dir))
        self.assertTrue(result)
        self.assertTrue(test_dir.exists())
        
        # 目录已存在时
        result = FileManager.ensure_directory_exists(str(test_dir))
        self.assertTrue(result)
        
        # 清理
        test_dir.rmdir()
    
    def test_get_safe_filename(self):
        """测试获取安全文件名"""
        # 测试不安全字符替换
        unsafe_name = 'test<>:"/\\|?*file.txt'
        safe_name = FileManager.get_safe_filename(unsafe_name)
        self.assertEqual(safe_name, "test_________file.txt")
        
        # 测试空格和点号处理
        self.assertEqual(FileManager.get_safe_filename("  test  "), "test")
        self.assertEqual(FileManager.get_safe_filename("...test..."), "test")
        
        # 测试空文件名
        self.assertEqual(FileManager.get_safe_filename(""), "untitled")
        self.assertEqual(FileManager.get_safe_filename("   "), "untitled")
        
        # 测试正常文件名
        self.assertEqual(FileManager.get_safe_filename("normal_file.txt"), "normal_file.txt")
    
    def test_get_video_filename_without_extension(self):
        """测试获取不带扩展名的视频文件名"""
        # 测试各种路径格式
        self.assertEqual(
            FileManager.get_video_filename_without_extension("/path/to/video.mp4"),
            "video"
        )
        self.assertEqual(
            FileManager.get_video_filename_without_extension("video.avi"),
            "video"
        )
        self.assertEqual(
            FileManager.get_video_filename_without_extension("complex.name.mkv"),
            "complex.name"
        )
        
        # 测试无扩展名
        self.assertEqual(
            FileManager.get_video_filename_without_extension("video"),
            "video"
        )
    
    def test_get_unique_filename(self):
        """测试获取唯一文件名"""
        # 创建测试文件
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.touch()
        
        # 测试唯一文件名生成
        unique_path = FileManager.get_unique_filename(
            self.temp_dir, "test", "txt"
        )
        self.assertEqual(unique_path, str(Path(self.temp_dir) / "test_1.txt"))
        
        # 创建更多文件测试递增
        (Path(self.temp_dir) / "test_1.txt").touch()
        unique_path = FileManager.get_unique_filename(
            self.temp_dir, "test", "txt"
        )
        self.assertEqual(unique_path, str(Path(self.temp_dir) / "test_2.txt"))
        
        # 清理
        test_file.unlink()
        (Path(self.temp_dir) / "test_1.txt").unlink()
    
    def test_is_video_file(self):
        """测试视频文件格式检查"""
        # 测试支持的格式
        video_files = [
            "video.mp4", "movie.avi", "clip.mov", "film.mkv",
            "video.wmv", "clip.flv", "movie.webm", "video.m4v",
            "clip.3gp", "movie.ogv", "video.ts", "clip.mts"
        ]
        
        for video_file in video_files:
            self.assertTrue(FileManager.is_video_file(video_file))
        
        # 测试不支持的格式
        non_video_files = [
            "image.jpg", "audio.mp3", "document.pdf", "text.txt",
            "archive.zip", "data.json"
        ]
        
        for non_video_file in non_video_files:
            self.assertFalse(FileManager.is_video_file(non_video_file))
        
        # 测试大小写不敏感
        self.assertTrue(FileManager.is_video_file("VIDEO.MP4"))
        self.assertTrue(FileManager.is_video_file("Movie.AVI"))
    
    def test_get_file_size_string(self):
        """测试文件大小字符串格式化"""
        # 创建测试文件
        test_file = Path(self.temp_dir) / "size_test.txt"
        
        # 测试不同大小的文件
        with open(test_file, 'w') as f:
            f.write("x" * 500)  # 500 bytes
        
        size_str = FileManager.get_file_size_string(str(test_file))
        self.assertEqual(size_str, "500 B")
        
        # 测试不存在的文件
        non_existent = Path(self.temp_dir) / "non_existent.txt"
        size_str = FileManager.get_file_size_string(str(non_existent))
        self.assertEqual(size_str, "未知大小")
        
        # 清理
        test_file.unlink()


class TestImageProcessor(unittest.TestCase):
    """图像处理工具测试类"""
    
    def test_get_image_info_with_invalid_file(self):
        """测试获取无效图像文件信息"""
        # 测试不存在的文件
        result = ImageProcessor.get_image_info("non_existent.jpg")
        self.assertIsNone(result)
    
    def test_create_thumbnail_with_invalid_file(self):
        """测试创建无效图像的缩略图"""
        # 测试不存在的文件
        result = ImageProcessor.create_thumbnail(
            "non_existent.jpg", "thumbnail.jpg"
        )
        self.assertFalse(result)


def run_utils_tests():
    """运行工具函数测试"""
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_suite.addTests(loader.loadTestsFromTestCase(TestTimeFormatter))
    test_suite.addTests(loader.loadTestsFromTestCase(TestFileManager))
    test_suite.addTests(loader.loadTestsFromTestCase(TestImageProcessor))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("=" * 60)
    print("工具函数单元测试")
    print("=" * 60)
    
    success = run_utils_tests()
    
    if success:
        print("\n🎉 所有工具函数测试通过！")
    else:
        print("\n❌ 部分工具函数测试失败")
    
    exit(0 if success else 1)