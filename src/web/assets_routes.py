# src/web/assets_routes.py
from flask import send_from_directory, request
import os

def register_assets_routes(app):
    """Register assets routes with recursive search logic"""
    
    @app.route('/media/<path:filename>')
    def assets_static(filename):
        # [DYNAMIC ROOT DISCOVERY] Proyektin ana qovluğunu tap
        current_file = os.path.abspath(__file__)  # src/web/assets_routes.py
        project_root = os.path.abspath(os.path.join(current_file, "..", ".."))
        
        # [RECURSIVE SEARCH LOGIC] 3 yerdə axtar
        search_paths = [
            os.path.join(project_root, "assets"),                    # birbaşa kökdə
            os.path.join(project_root, "assets", "table_images"),  # masa ikonları
            os.path.join(project_root, "assets", "menu_images"),   # menyu şəkilləri
        ]
        
        # [SMART DELIVERY] Fayl harada tapsa, oradan göndər
        for search_path in search_paths:
            full_path = os.path.join(search_path, filename)
            if os.path.exists(full_path) and os.path.isfile(full_path):
                # [DEBUG LOGGING] Uğurlu tapma
                print(f"DEBUG: Fayl tapildi: {full_path}")
                
                # [SECURITY] Anti-bloklama başlıqları
                response = send_from_directory(search_path, filename)
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response
        
        # [DEBUG LOGGING] Fayl tapılmadı
        print(f"DEBUG: Axtarilan tam yollar:")
        for search_path in search_paths:
            full_path = os.path.join(search_path, filename)
            print(f"  - {full_path} (movcud deyil)")
        
        # Fayl tapılmadıqda 404 qaytar
        from flask import abort
        abort(404)
    
    return app
