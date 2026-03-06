### 1) Optimizasiya Xülasəsi

- **Cari optimizasiya vəziyyəti:** Əsas funksionallıq mövcuddur, amma oxunuş-ağır endpoint-lərdə və ödəniş axınlarında bahalı yaddaşdaxili emal (`.all()` + Python dövrləri), təkrarlanan sorğular və N+1 nümunələri var. Bu, yük artdıqca performansı zəiflədib DB/CPU xərclərini artıracaq.
- **Ən yüksək təsirli ilk 3 yaxşılaşdırma:**
  1. Hesabat/ödəniş xülasələrində tam-fetch yanaşmasını DB tərəfində aqreqasiya/grouping ilə əvəz etmək.
  2. Sifariş/ödəniş/hesabat yollarında N+1 sorğularını eager loading + batch yükləmə ilə aradan qaldırmaq.
  3. İsti filtrlər üçün (`created_at`, `status`, `table_id`, `customer_id`) hədəfli indekslər əlavə etmək və gün-gün təkrarlanan sorğu fanout-unu azaltmaq.
- **Dəyişiklik edilməzsə ən böyük risk:** Məlumat həcmi artdıqca request gecikməsi və DB yükü qeyri-xətti artacaq (xüsusilə hesabat və checkout), nəticədə UI/API cavabları ləngiyəcək və ödəniş anında dar boğaz yaranacaq.

### 2) Tapıntılar (Prioritetli)

- **Başlıq:** Hesabatlar bütün payment/order dataset-ni yükləyib Python-da aqreqasiya edir
- **Kateqoriya** (DB / Alqoritm)
- **Səviyyə:** High
- **Təsir:** Hesabat gecikməsini, DB transfer ölçüsünü və web worker CPU istifadəsini azaldır.
- **Sübut:** `daily_summary` və `monthly_summary` tam sətirləri çəkib Python-da cəmləyir/group edir; `yearly_summary` `monthly_summary`-ni 12 dəfə çağırır (12 ayrıca skan). `api_weekly` hər sorğuda `daily_summary`-ni 7 dəfə işlədir. (`modules/reports/report_service.py`, `web/routes/reports.py`)
- **Niyə səmərəsizdir:** Sadə total/count üçün bütöv obyekt qraflarını çəkmək I/O və Python CPU xərcini artırır; oxşar tarix pəncərələrinin təkrarı əlavə overhead yaradır.
- **Tövsiyə olunan düzəliş:**
  - SQL aqreqasiyası (`func.sum`, `func.count`, method/day/month üzrə group) istifadə edib skalyar nəticə qaytarın.
  - 7x/12x dövrləri həftəlik/aylıq/illik binlər üçün tək grouped sorğu ilə əvəz edin.
  - ORM entity yerinə yalnız lazım olan sütunları seçin.
- **Tradeoff / Risk:** SQL ifadə məntiqi bir qədər mürəkkəbləşir; timezone/tarix pəncərəsi semantikası yoxlanmalıdır.
- **Gözlənən təsir:** **High** (adətən 50–90% daha az transfer olunan sətir və məlumat artdıqca ciddi cavab sürəti qazancı).
- **Silinmə Təhlükəsizliyi:** Likely Safe
- **Yenidən İstifadə Əhatəsi:** service-wide (hesabat modulu + hesabat API-ləri)
- **Təsnifat:** Reuse Opportunity (mərkəzləşdirilmiş aqreqasiya helper-i), Over-Abstracted Code (sətir siyahıları üzərində dövr edən xülasələr)

- **Başlıq:** Ödənişdə stok sərfiyyatı hər order item/recipe line üçün N+1 sorğu yaradır
- **Kateqoriya** (DB / Etibarlılıq / Xərc)
- **Səviyyə:** High
- **Təsir:** Çox-item sifarişlərdə checkout sürətlənir, lock müddəti və DB round-trip azalır, ödəniş anında contention riski enir.
- **Sübut:** `_consume_inventory_for_order` daxilində hər order item recipe sorğusu yaradır, sonra hər recipe line ayrıca inventory sorğusu atır; fallback yolunda da hər item üçün inventory sorğusu var. (`modules/pos/pos_service.py`)
- **Niyə səmərəsizdir:** Sorğu sayı `items × recipe_lines` ilə böyüyür; bu da biznes baxımından ən kritik olan checkout yolunda gecikmə yaradır.
- **Tövsiyə olunan düzəliş:**
  - `order.items` + `menu_item` + aktiv recipe-ləri bulk şəkildə əvvəlcədən yükləyin.
  - Lazım olan inventory ID-ləri toplayıb bütün `InventoryItem` sətirlərini tək sorğu/map ilə yükləyin.
  - Sərfiyyatı yaddaşda hesablayıb adjustment-ları bir tranzaksiyada batch yazın.
- **Tradeoff / Risk:** Batch məntiqi daha mürəkkəb olur; stok doğrulaması və xəta mesajlarının deterministik qalması yoxlanmalıdır.
- **Gözlənən təsir:** **High** (sorğu sayı order başına O(n*m)-dən O(1–3) batch-ə enir).
- **Silinmə Təhlükəsizliyi:** Needs Verification
- **Yenidən İstifadə Əhatəsi:** module-wide (POS + gələcək stok sərfiyyatı axınları)
- **Təsnifat:** Reuse Opportunity (ortaq preload utiliti)

- **Başlıq:** Order/report serializasiyası böyük ehtimalla relation N+1 yüklənmələri yaradır
- **Kateqoriya** (DB / I/O)
- **Səviyyə:** Medium
- **Təsir:** Request başına DB chatter azalır, order/report səhifələrində p95 gecikməsi yaxşılaşır.
- **Sübut:** `completed_sales` order-lar üzərində dövr edib `order.items`, `item.menu_item`, `order.table`, `order.waiter` sahələrinə daxil olur; order API-lərində də explicit eager-loading olmadan relation sahələri iterasiya edilir. (`modules/reports/report_service.py`, `web/routes/orders.py`)
- **Niyə səmərəsizdir:** Default lazy-loading hər sətir/relation üçün əlavə sorğu yarada bilər.
- **Tövsiyə olunan düzəliş:** List/detail endpoint-lərdə bilinən relation-lar üçün `selectinload/joinedload` tətbiq edin; payload formalaşdırmanı bir keçiddə saxlayın.
- **Tradeoff / Risk:** Düzgün scope edilməzsə over-eager loading lazımsız data çəkə bilər.
- **Gözlənən təsir:** **Medium/High** (order ölçüsü və relation dərinliyindən asılıdır).
- **Silinmə Təhlükəsizliyi:** Likely Safe
- **Yenidən İstifadə Əhatəsi:** service-wide
- **Təsnifat:** Reuse Opportunity (standart eager-loading query builder-lər)

- **Başlıq:** Rezervasiya uyğunluğu və konflikt yoxlaması tam sətirləri Python-da filtr edir
- **Kateqoriya** (DB / Alqoritm)
- **Səviyyə:** Medium
- **Təsir:** Pik saatlarda rezervasiya yoxlaması sürətlənir, DB və tətbiq CPU yükü azalır.
- **Sübut:** `create` eyni gün/masa rezervasiyalarını hamısını çəkib 2 saat pəncərəsini Python-da yoxlayır; `get_available_tables` bütün aktiv masaları və günün rezervasiyalarını çəkib Python-da filtr edir. (`modules/reservation/reservation_service.py`)
- **Niyə səmərəsizdir:** Tətbiq səviyyəsində filtrasiya rezervasiya həcmi və masa sayı artdıqca zəif miqyaslanır.
- **Tövsiyə olunan düzəliş:**
  - Vaxt pəncərəsi konfliktlərini SQL predicate-lərinə köçürün.
  - Mövcud masaları konfliktli rezervasiyalar üzərində anti-join / `NOT IN` alt sorğusu ilə qaytarın.
- **Tradeoff / Risk:** Datetime arifmetikasının DB-lər arasında portativliyi yoxlanmalıdır.
- **Gözlənən təsir:** **Medium** (pik rezervasiya trafikində nəzərəçarpan).
- **Silinmə Təhlükəsizliyi:** Needs Verification
- **Yenidən İstifadə Əhatəsi:** local file / module
- **Təsnifat:** Over-Abstracted Code (set-based DB məntiqi əvəzinə manual list filtrasiya)

- **Başlıq:** Dominant filter/sort üçün hədəfli indekslər çatışmır
- **Kateqoriya** (DB)
- **Səviyyə:** Medium
- **Təsir:** Oxunuş və hesabat gecikməsi yaxşılaşır; full-scan təzyiqi və infra xərci azalır.
- **Sübut:** Xidmətlərdə/routelarda `created_at`, `status`, `table_id`, `customer_id`, rezervasiya tarix sahələri tez-tez filtr olunur; model təriflərində əsasən PK və az sayda unique indeks var. (`database/models.py`, `modules/orders/order_service.py`, `modules/reports/report_service.py`, `modules/reservation/reservation_service.py`)
- **Niyə səmərəsizdir:** Dəstəkləyici indekslər olmadan tarix aralığı/status sorğuları data artdıqca scan-a çevrilir.
- **Tövsiyə olunan düzəliş:** Sorğu formalarına uyğun composite indekslər əlavə edin, məsələn `(created_at, status)`, `(table_id, status, created_at)`, `(customer_id, status)`, `(date, table_id, is_cancelled)`.
- **Tradeoff / Risk:** Yazma əməliyyatları bir qədər yavaşlayır və indeks storage artır.
- **Gözlənən təsir:** **Medium/High** (oxunuş-ağır mühitlərdə).
- **Silinmə Təhlükəsizliyi:** Likely Safe
- **Yenidən İstifadə Əhatəsi:** service-wide
- **Təsnifat:** Reuse Opportunity (ortaq indeks strategiyası)

- **Başlıq:** Summary/count endpoint-lər skalyar saylar əvəzinə tam entity yükləyir
- **Kateqoriya** (DB / Xərc)
- **Səviyyə:** Medium
- **Təsir:** Dashboard/xülasə endpoint-lərdə yaddaş və CPU istifadəsi azalır.
- **Sübut:** `get_today_summary` bu günün order-larını tam yükləyib bir neçə Python list scan edir; loyallıq xülasələrində də oxşar full-load nümunələri var. (`modules/orders/order_service.py`, `modules/loyalty/loyalty_service.py`)
- **Niyə səmərəsizdir:** Yalnız count/sum lazım olduqda ORM obyektlərini hydrate etmək artıq xərcdir.
- **Tövsiyə olunan düzəliş:** Aqreqat sorğularına (`count`, şərti sum) keçin və minimal skalyar projection qaytarın.
- **Tradeoff / Risk:** Helper-lə bükülməzsə oxunaqlılıq bir qədər azala bilər.
- **Gözlənən təsir:** **Medium**.
- **Silinmə Təhlükəsizliyi:** Likely Safe
- **Yenidən İstifadə Əhatəsi:** module/service-wide
- **Təsnifat:** Reuse Opportunity (ortaq summary query utilitiləri)

- **Başlıq:** Startup auto-migrate hər açılışda sxemi inspect edib ALTER cəhdləri edir
- **Kateqoriya** (Etibarlılıq / Xərc)
- **Səviyyə:** Low
- **Təsir:** Daha sürətli startup və prod mühitdə daha az əməliyyat riski.
- **Sübut:** `init_database` həmişə `_auto_migrate` çağırır; bu funksiya hər startup-da cədvəl/sütun inspect edib şərti ALTER icra edir. (`database/connection.py`)
- **Niyə səmərəsizdir:** Startup zamanı schema scan/DDL yoxlaması əlavə overhead yaradır və çox-instans mühitdə riskli ola bilər.
- **Tövsiyə olunan düzəliş:** Auto-migrate-i env flag ilə idarə edin; prod-da Alembic axınına etibar edin.
- **Tradeoff / Risk:** Deploy zamanı migrasiya disiplininə daha çox ehtiyac olur.
- **Gözlənən təsir:** **Low/Medium** (startup/ops yaxşılaşması).
- **Silinmə Təhlükəsizliyi:** Needs Verification
- **Yenidən İstifadə Əhatəsi:** service-wide
- **Təsnifat:** Over-Abstracted Code (runtime migration məntiqi migration alətinin funksiyasını təkrarlayır)

- **Başlıq:** Kiçik dead/duplicate nümunələr optimizasiya baxımından texniki borcu artırır
- **Kateqoriya** (Build / Maintainability)
- **Səviyyə:** Low
- **Təsir:** Koqnitiv yükü və drift riskini azaldan kiçik, amma faydalı qazanc.
- **Sübut:** Modul üzrə təkrarlanan summary məntiqi və xırda istifadə olunmayan/duplikat nümunələr (məs., istifadə olunmayan `typing` import-u). (`modules/loyalty/loyalty_service.py` və oxşar servis faylları)
- **Niyə səmərəsizdir:** Dead/duplikat kod audit səthini böyüdür və gələcək refaktor/optimizasiyanı ləngidir.
- **Tövsiyə olunan düzəliş:** İstifadəsiz import/branch-ləri təmizləyin, təkrarlanan summary məntiqlərini ortaq helper-lərdə birləşdirin.
- **Tradeoff / Risk:** Minimaldır; lint/typecheck keçidini yoxlamaq kifayətdir.
- **Gözlənən təsir:** Runtime baxımından **Low**, maintainability baxımından **Medium**.
- **Silinmə Təhlükəsizliyi:** Safe
- **Yenidən İstifadə Əhatəsi:** service-wide
- **Təsnifat:** Dead Code, Reuse Opportunity

### 3) Sürətli Qazanclar (İlk Bunları Et)

1. `daily_summary`, `monthly_summary`, `get_today_summary`, `get_summary` funksiyalarını SQL aqreqatlarına çevirin (tez tətbiq, yüksək təsir).
2. Report/order detail serializasiyasında eager loading əlavə edib böyük refaktor olmadan N+1 davranışını azaldın.
3. `orders/payments/reservations` üçün tarix+status filtrlərinə prioritet indekslər əlavə edin.
4. Həftəlik/illik dövrləri grouped aqreqat sorğuları ilə əvəz edin (həftəlik tək sorğu, illik/aylıq bucket-lər üçün tək sorğu).
5. UI-da böyüyə bilən list endpoint-lərə pagination/limit tətbiq edin.

### 4) Dərin Optimizasiyalar (Növbəti Mərhələ)

- Dashboard/report endpoint-ləri üçün ayrıca read-model/reporting qatını (materialized daily aggregate və ya cache cədvəlləri) tətbiq edin.
- Stok sərfiyyatını “planı hesabla, sonra tətbiq et” tipli deterministik pipeline-a çevirin; read/write batch-ləmə və idempotency qoruyucuları əlavə edin.
- Endpoint üzrə explicit loader options ilə standart query builder-lər yaradın ki, performans xüsusiyyətləri ölçülə və idarə oluna bilsin.
- Təkrarlanan bahalı xülasələri qısaömürlü cache arxasına alın (məs., dashboard üçün 30–120 saniyə TTL).

### 5) Doğrulama Planı

- **Benchmark-lar**
  - Əsas endpoint-lərdə baseline çıxarın: `/dashboard`, `/reports`, `/reports/api/weekly`, `/orders/api/<id>`, payment API.
  - Realistik concurrency (məs., 20/50/100 VU) və prod-a yaxın seed edilmiş data ilə load test edin.
- **Profilinq strategiyası**
  - Request başına SQLAlchemy query logging/query count instrumentasiyasını aktiv edin.
  - Endpoint üzrə ölçün: query sayı, ümumi DB vaxtı, ORM obyekt sayı, cavab vaxtı percentiləri.
  - Ən ağır sorğular üçün indeks/sorğu dəyişikliyindən əvvəl/sonra DB `EXPLAIN (ANALYZE)` müqayisəsi aparın.
- **Əvvəl/Sonra müqayisə metrikləri**
  - p50/p95/p99 gecikmə
  - Request başına sorğu sayı
  - Scan olunan sətir / qaytarılan sətir
  - App worker CPU vaxtı
  - Paralel checkout zamanı payment endpoint uğurlu cavab gecikməsi
- **Düzgünlük testləri**
  - Hesabat total-ları üçün regressiya testləri (günlük/həftəlik/aylıq/illik uyğunluq).
  - Discount + loyallıq + yetərsiz stok ssenariləri ilə checkout testləri.
  - Sərhəd saatlarında rezervasiya konflikt edge-case testləri.
  - Inventory adjustment və yekun stok tutarlılığı yoxlamaları.

### 6) Optimallaşdırılmış Kod / Patch (mümkündürsə)

İstəyə uyğun olaraq runtime kod dəyişikliyi edilməyib. Bu sənəd yalnız optimizasiya auditidir.

Yüksək ROI üçün pseudo-patch istiqaməti:

- Tam-fetch xülasələri aqreqat sorğularla əvəz edin:
  - `SELECT SUM(final_amount), SUM(discount_amount), COUNT(*) FROM payments WHERE created_at BETWEEN :start AND :end`
  - `SELECT method, SUM(final_amount) FROM payments ... GROUP BY method`
- Həftəlik dövrü grouped sorğu ilə əvəz edin:
  - `SELECT DATE(created_at) AS d, SUM(final_amount) FROM payments WHERE created_at >= :week_start GROUP BY d`
- Loader options əlavə edin:
  - `query(Order).options(selectinload(Order.items).selectinload(OrderItem.menu_item), joinedload(Order.table), joinedload(Order.waiter))`
- Migrasiya ilə indekslər əlavə edin:
  - `orders(created_at, status)`, `orders(table_id, status, created_at)`, `payments(created_at, method)`, `reservations(date, table_id, is_cancelled)`
