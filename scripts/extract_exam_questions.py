#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
灵测 LingCe — 考试题目抽取脚本
从题库中抽取44道题作为考试题：20道单选、20道多选、4道简答
支持指定必须包含的题目ID

使用方法：
python extract_exam_questions.py <题库文件路径> [必须包含的题目ID]

示例：
python extract_exam_questions.py data/questions.json
python extract_exam_questions.py data/questions.json 9
python extract_exam_questions.py data/questions.json 9,10,11
"""

import json
import random
import sys
import os
from typing import List, Dict, Any, Set


class ExamQuestionExtractor:
    """考试题目抽取器"""
    
    def __init__(self, question_bank_path: str):
        self.question_bank_path = question_bank_path
        self.questions = []
        self.load_question_bank()
    
    def load_question_bank(self):
        """加载题库"""
        try:
            with open(self.question_bank_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # 处理不同的题库格式
                if isinstance(data, list):
                    # 直接是题目数组
                    self.questions = data
                elif isinstance(data, dict) and 'questions' in data:
                    # 包含questions字段的对象
                    self.questions = data['questions']
                else:
                    print(f"不支持的题库文件格式")
                    sys.exit(1)
                    
            print(f"加载题库：{len(self.questions)} 道题目")
        except FileNotFoundError:
            print(f"找不到题库文件 {self.question_bank_path}")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"题库文件格式不正确 {self.question_bank_path}")
            sys.exit(1)
        except Exception as e:
            print(f"加载题库失败 {str(e)}")
            sys.exit(1)
    
    def categorize_questions(self) -> Dict[str, List[Dict]]:
        """按题型分类题目"""
        categories = {
            'single': [],    # 单选题
            'multiple': [],  # 多选题
            'short': [],     # 简答题
            'judge': [],     # 判断题
            'fill': []       # 填空题
        }
        
        for question in self.questions:
            question_type = question.get('type', '').lower()
            if question_type in categories:
                categories[question_type].append(question)
        
        return categories
    
    def find_questions_by_ids(self, required_ids: Set[int]) -> Dict[str, List[Dict]]:
        """根据ID查找题目并按类型分类"""
        found_questions = {
            'single': [],
            'multiple': [],
            'short': [],
            'judge': [],
            'fill': []
        }
        
        found_ids = set()
        
        for question in self.questions:
            question_id = question.get('id')
            if question_id in required_ids:
                question_type = question.get('type', '').lower()
                if question_type in found_questions:
                    found_questions[question_type].append(question)
                    found_ids.add(question_id)
        
        # 检查是否所有指定的ID都找到了
        missing_ids = required_ids - found_ids
        if missing_ids:
            print(f"未找到ID：{sorted(missing_ids)}")
        
        return found_questions
    
    def extract_exam_questions(self, required_ids: Set[int] = None) -> List[Dict]:
        """抽取考试题目"""
        # 目标数量
        target_counts = {
            'single': 20,    # 20道单选题
            'multiple': 20,  # 20道多选题
            'short': 4       # 4道简答题
        }
        
        # 按类型分类所有题目
        all_categories = self.categorize_questions()
        
        # 检查题目数量是否足够
        for question_type, target_count in target_counts.items():
            available_count = len(all_categories[question_type])
            if available_count < target_count:
                print(f"{question_type}题目不足：需要{target_count}道，实际{available_count}道")
        
        # 处理必须包含的题目
        required_questions = {
            'single': [],
            'multiple': [],
            'short': []
        }
        
        if required_ids:
            found_required = self.find_questions_by_ids(required_ids)
            for question_type in target_counts.keys():
                required_questions[question_type] = found_required[question_type]
                if len(required_questions[question_type]) > 0:
                    print(f"包含指定{question_type}题目：{len(required_questions[question_type])}道")
        
        # 抽取题目
        selected_questions = []
        
        for question_type, target_count in target_counts.items():
            # 必须包含的题目
            required_list = required_questions[question_type]
            selected_from_type = required_list.copy()
            
            # 从剩余题目中随机抽取
            available_questions = [q for q in all_categories[question_type] 
                                 if q not in required_list]
            
            remaining_needed = target_count - len(selected_from_type)
            if remaining_needed > 0:
                if len(available_questions) >= remaining_needed:
                    additional_questions = random.sample(available_questions, remaining_needed)
                    selected_from_type.extend(additional_questions)
                else:
                    # 如果不够，就全部加入
                    selected_from_type.extend(available_questions)
                    print(f"{question_type}题目不足，实际抽取{len(selected_from_type)}道")
            
            selected_questions.extend(selected_from_type)
        
        # 打乱题目顺序
        random.shuffle(selected_questions)
        
        # 直接返回题目数组，跟原题库格式一样
        return selected_questions
    
    def save_exam_questions(self, questions: List[Dict], output_path: str):
        """保存考试题目到文件"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(questions, f, ensure_ascii=False, indent=2)
            print(f"已保存到：{output_path}")
        except Exception as e:
            print(f"保存文件失败 {str(e)}")
            sys.exit(1)
    
    def print_statistics(self, questions: List[Dict]):
        """打印统计信息"""
        # 统计各类型题目数量
        type_counts = {}
        for question in questions:
            question_type = question.get('type', 'unknown')
            type_counts[question_type] = type_counts.get(question_type, 0) + 1
        
        print(f"\n总题目数：{len(questions)}")
        
        type_names = {
            'single': '单选题',
            'multiple': '多选题',
            'short': '简答题',
            'judge': '判断题',
            'fill': '填空题'
        }
        
        for question_type, count in type_counts.items():
            type_name = type_names.get(question_type, question_type)
            print(f"{type_name}：{count}道")
        
        # 显示题目ID列表
        question_ids = [q.get('id', 0) for q in questions]
        question_ids.sort()
        print(f"\n题目ID：{question_ids}")


def parse_required_ids(ids_str: str) -> Set[int]:
    """解析必须包含的题目ID"""
    if not ids_str:
        return set()
    
    try:
        ids = set()
        for id_part in ids_str.split(','):
            ids.add(int(id_part.strip()))
        return ids
    except ValueError:
        print("题目ID必须是数字，多个ID用逗号分隔")
        sys.exit(1)


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法：")
        print("python extract_exam_questions.py <题库文件路径> [必须包含的题目ID]")
        print("\n示例：")
        print("python extract_exam_questions.py data/questions.json")
        print("python extract_exam_questions.py data/questions.json 9")
        print("python extract_exam_questions.py data/questions.json 9,10,11")
        sys.exit(1)
    
    # 解析命令行参数
    question_bank_path = sys.argv[1]
    required_ids_str = sys.argv[2] if len(sys.argv) > 2 else ""
    
    # 检查题库文件是否存在
    if not os.path.exists(question_bank_path):
        print(f"题库文件不存在 {question_bank_path}")
        sys.exit(1)
    
    # 解析必须包含的题目ID
    required_ids = parse_required_ids(required_ids_str)
    if required_ids:
        print(f"必须包含题目ID：{sorted(required_ids)}")
    
    # 创建抽取器
    extractor = ExamQuestionExtractor(question_bank_path)
    
    # 抽取考试题目
    print("\n开始抽取...")
    questions = extractor.extract_exam_questions(required_ids)
    
    # 生成输出文件名
    base_name = os.path.splitext(os.path.basename(question_bank_path))[0]
    output_path = f"exam_{base_name}_{random.randint(1000, 9999)}.json"
    
    # 保存考试题目
    extractor.save_exam_questions(questions, output_path)
    
    # 打印统计信息
    extractor.print_statistics(questions)
    
    print(f"\n抽取完成！")


if __name__ == "__main__":
    main()