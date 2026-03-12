#!/usr/bin/env python3
"""
Ramo Pub Project Cleanup Script
Identifies and removes duplicate files and directories
"""

import os
import shutil
from pathlib import Path
from typing import List, Tuple, Dict

class ProjectCleanup:
    """Proyekt təmizləmə aləti"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.duplicates_found = []
        self.space_saved = 0
        
    def scan_duplicates(self) -> Dict[str, List[Path]]:
        """Dublikat faylları tap"""
        duplicates = {}
        
        # 1. Main.py faylları
        main_files = list(self.project_root.glob("**/main.py"))
        if len(main_files) > 1:
            duplicates["main.py"] = main_files
            
        # 2. Requirements faylları
        req_files = list(self.project_root.glob("**/requirements*.txt"))
        if len(req_files) > 1:
            duplicates["requirements"] = req_files
            
        # 3. Dublikat qovluq strukturları
        desktop_dirs = list(self.project_root.glob("**/desktop"))
        if len(desktop_dirs) > 1:
            duplicates["desktop_dirs"] = desktop_dirs
            
        # 4. Assets qovluqları (əgər varsa)
        assets_dirs = list(self.project_root.glob("**/assets"))
        if len(assets_dirs) > 1:
            duplicates["assets_dirs"] = assets_dirs
            
        # 5. Run_desktop faylları
        run_desktop_files = list(self.project_root.glob("**/run_desktop.py"))
        if len(run_desktop_files) > 1:
            duplicates["run_desktop"] = run_desktop_files
            
        # 6. Main_window faylları
        main_window_files = list(self.project_root.glob("**/main_window.py"))
        if len(main_window_files) > 1:
            duplicates["main_window"] = main_window_files
            
        # 7. README faylları
        readme_files = list(self.project_root.glob("**/README.md"))
        if len(readme_files) > 1:
            duplicates["readme"] = readme_files
            
        return duplicates
    
    def calculate_size(self, path: Path) -> int:
        """Fayl və ya qovluq ölçüsünü hesabla"""
        if path.is_file():
            return path.stat().st_size
        elif path.is_dir():
            total = 0
            for item in path.rglob("*"):
                if item.is_file():
                    total += item.stat().st_size
            return total
        return 0
    
    def generate_report(self, duplicates: Dict[str, List[Path]]) -> str:
        """Dublikat hesabatı hazırla"""
        report = []
        report.append("=" * 80)
        report.append("RAMO PUB PROYEKT DUPLIKAT ANALIZ HESABATI")
        report.append("=" * 80)
        report.append("")
        
        total_space = 0
        
        for category, files in duplicates.items():
            report.append(f"KATEGORIYA: {category}")
            report.append("-" * 60)
            
            for i, file_path in enumerate(files):
                size = self.calculate_size(file_path)
                size_mb = size / (1024 * 1024)
                total_space += size
                
                status = "ESAS" if i == 0 else "DUPLIKAT"
                relative_path = file_path.relative_to(self.project_root)
                
                report.append(f"  [{status}] {relative_path}")
                report.append(f"         Olcu: {size_mb:.2f} MB")
                report.append(f"         Yol: {file_path}")
                report.append("")
        
        total_mb = total_space / (1024 * 1024)
        report.append("=" * 80)
        report.append(f"CEMI: {total_mb:.2f} MB dublikat fayl")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def get_safe_to_remove(self, duplicates: Dict[str, List[Path]]) -> List[Path]:
        """Təhlükəsiz silinəcək faylları təyin et"""
        safe_to_remove = []
        
        for category, files in duplicates.items():
            if len(files) <= 1:
                continue
                
            # Əsas faylı saxla, qalanlarını sil
            if category == "main.py":
                # Kökdəki main.py əsasdır, src/main.py Docker üçündür
                for file_path in files:
                    if "src/main.py" in str(file_path):
                        safe_to_remove.append(file_path)
                        
            elif category == "requirements":
                # requirements/requirements.txt əsasdır
                for file_path in files:
                    if "src/desktop/" in str(file_path):
                        safe_to_remove.append(file_path)
                        
            elif category == "desktop_dirs":
                # src/desktop/desktop/ dublikatdır
                for dir_path in files:
                    if "src/desktop/desktop" in str(dir_path):
                        safe_to_remove.append(dir_path)
                        
            elif category == "run_desktop":
                # src/desktop/run_desktop.py dublikatdır
                for file_path in files:
                    if "src/desktop/" in str(file_path):
                        safe_to_remove.append(file_path)
                        
            elif category == "main_window":
                # src/desktop/desktop/main_window.py dublikatdır
                for file_path in files:
                    if "src/desktop/desktop/" in str(file_path):
                        safe_to_remove.append(file_path)
                        
            elif category == "readme":
                # src/desktop/desktop/README.md dublikatdır
                for file_path in files:
                    if "src/desktop/desktop/" in str(file_path):
                        safe_to_remove.append(file_path)
        
        return safe_to_remove
    
    def remove_duplicates(self, files_to_remove: List[Path]) -> None:
        """Dublikatları sil"""
        for file_path in files_to_remove:
            try:
                size = self.calculate_size(file_path)
                self.space_saved += size
                
                if file_path.is_dir():
                    shutil.rmtree(file_path)
                    print(f"Qovluq silindi: {file_path}")
                else:
                    file_path.unlink()
                    print(f"Fayl silindi: {file_path}")
                    
            except Exception as e:
                print(f"Xeta: {file_path} - {e}")
    
    def run_cleanup(self, dry_run: bool = True) -> None:
        """Təmizləmə əməliyyatını icra et"""
        print("Proyekt dublikatları skan edilir...")
        
        duplicates = self.scan_duplicates()
        
        if not duplicates:
            print("Heç bir dublikat tapilmadi!")
            return
        
        # Hesabat çap et
        report = self.generate_report(duplicates)
        print(report)
        
        if dry_run:
            print("\n" + "=" * 80)
            print("DRY RUN MODE - Heç bir fayl silinmədi")
            print("Silmək üçün: python cleanup_duplicates.py --execute")
            print("=" * 80)
            return
        
        # Təsdiq al
        print("\n" + "=" * 80)
        response = input("Bu dublikatları silmək istəyirsiniz? (yes/no): ").lower().strip()
        
        if response in ['yes', 'y', 'bəli', 'b']:
            safe_to_remove = self.get_safe_to_remove(duplicates)
            
            if safe_to_remove:
                print(f"\n{len(safe_to_remove)} fayl/qovluq silinir...")
                self.remove_duplicates(safe_to_remove)
                
                saved_mb = self.space_saved / (1024 * 1024)
                print(f"\n✅ Təmizləmə tamamlandı!")
                print(f"Qənaşdırılan yer: {saved_mb:.2f} MB")
            else:
                print("Təhlükəsiz silinəcək fayl tapılmadı.")
        else:
            print("Əməliyyat ləğv edildi.")

def main():
    """Əsas funksiya"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ramo Pub Project Cleanup Tool")
    parser.add_argument("--execute", action="store_true", 
                   help="Dublikatları sil (default: dry run)")
    parser.add_argument("--project-root", type=str, 
                   default=".", help="Proyektin ana kökü")
    
    args = parser.parse_args()
    
    project_root = Path(args.project_root).resolve()
    cleanup = ProjectCleanup(project_root)
    
    print(f"Proyekt koku: {project_root}")
    print()
    
    cleanup.run_cleanup(dry_run=not args.execute)

if __name__ == "__main__":
    main()
