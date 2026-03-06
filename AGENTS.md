# AGENTS.md

## Mütləq əməl ediləcək qaydalar
- `OPTIMIZATIONS.md` yalnız audit sənədidir; həmin fayla runtime kod dəyişikliyi qarışdırmayın.
- Sxem dəyişikliklərində Alembic migrasiyalarına üstünlük verin; ayrıca istənmədikcə `database/connection.py` daxilində runtime sxem mutasiyasını artırmayın.
- Endpoint dəyişdirərkən `permission_required` / `permission_required_api` icazə yoxlamalarını qoruyun.
- Sifariş/ödəniş/anbar yeniləmələrini tək DB tranzaksiya axınında saxlayın; checkout axınında commit nöqtələrini parçalamayın.

## Bitirməzdən əvvəl yoxlama
- İşlədin: `pytest -q`
- İşlədin: `python -m compileall modules web database`

## Repo-ya xas konvensiyalar
- Biznes məntiqi `modules/*/*_service.py` fayllarında olur; `web/routes/*.py` handler-ləri nazik saxlayın və məntiqi servis qatına ötürün.
- Route-larda `g.db` (Flask request-scoped session) istifadə edin; handler daxilində ad-hoc qlobal session yaratmayın.
- Bir neçə modulda soft-delete nümunəsi var (`is_active`, `is_cancelled`); ayrıca tələb yoxdursa hard delete etməyin.

## Vacib yerlər
- DB bootstrap / fallback / auto-migrate: `database/connection.py`
- Əsas ORM modelləri: `database/models.py`
- Checkout + stok sərfiyyatı axını: `modules/pos/pos_service.py`
- Hesabatlarda isti (hot) path-lər: `modules/reports/report_service.py`

## Dəyişiklik təhlükəsizliyi qaydaları
- Tapşırıq açıq şəkildə icazə vermirsə, `web/routes` altındakı mövcud route-ların API cavab açarlarını dəyişməyin.
- Hesabat/xülasə refaktorunda sorğu formasını optimizasiya etməzdən əvvəl mövcud rəqəmsal uyğunluğu (cəmlər/saylar) qoruyun.
