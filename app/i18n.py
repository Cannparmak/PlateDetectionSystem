"""Global TR/EN localization utilities for templates and API responses."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates

LANG_COOKIE_NAME = "site_lang"
SUPPORTED_LANGS = ("tr", "en")
DEFAULT_LANG = "tr"

TRANSLATIONS: dict[str, dict[str, str]] = {
    # ── Camera UI ────────────────────────────────────────────────────
    "cam_title":          {"tr": "Canlı Kamera",                  "en": "Live Camera"},
    "cam_entry":          {"tr": "Giriş",                         "en": "Entry"},
    "cam_exit":           {"tr": "Çıkış",                         "en": "Exit"},
    "cam_occupancy":      {"tr": "Doluluk",                       "en": "Occupancy"},
    "cam_source":         {"tr": "Kamera Kaynağı",                "en": "Camera Source"},
    "cam_start":          {"tr": "Başlat",                        "en": "Start"},
    "cam_live_detection": {"tr": "Canlı Tespit",                  "en": "Live Detection"},
    "admin_start_entry":  {"tr": "Giriş kamerasını başlatın",     "en": "Start the entry camera"},
    "admin_start_exit":   {"tr": "Çıkış kamerasını başlatın",     "en": "Start the exit camera"},
    # ── Admin / Dashboard ─────────────────────────────────────────────
    "admin_dashboard":    {"tr": "Admin Dashboard",               "en": "Admin Dashboard"},
    "admin_reports":      {"tr": "Raporlar",                      "en": "Reports"},
    "admin_users":        {"tr": "Kullanıcılar",                  "en": "Users"},
    "admin_disable":      {"tr": "Devre Dışı",                    "en": "Disable"},
    "admin_inside":       {"tr": "İçeride",                       "en": "Inside"},
    "admin_records":      {"tr": "kayıt",                         "en": "records"},
    "admin_daily_avg":    {"tr": "Günlük Ortalama",               "en": "Daily Average"},
    "admin_total":        {"tr": "Toplam",                        "en": "Total"},
    # ── Common buttons ────────────────────────────────────────────────
    "btn_cancel":         {"tr": "İptal",                         "en": "Cancel"},
    "btn_confirm":        {"tr": "Onayla",                        "en": "Confirm"},
    "btn_edit":           {"tr": "Düzenle",                       "en": "Edit"},
    "btn_update":         {"tr": "Güncelle",                      "en": "Update"},
    # ── Customers ────────────────────────────────────────────────────
    "cust_title":         {"tr": "Müşteriler",                    "en": "Customers"},
    "cust_new":           {"tr": "Yeni Müşteri",                  "en": "New Customer"},
    "cust_edit":          {"tr": "Müşteri Düzenle",               "en": "Edit Customer"},
    "cust_search":        {"tr": "İsim, telefon ara...",          "en": "Search name, phone..."},
    "cust_detail":        {"tr": "Detay",                         "en": "Detail"},
    "cust_contact":       {"tr": "İletişim",                      "en": "Contact"},
    "cust_summary":       {"tr": "Özet",                          "en": "Summary"},
    "cust_vehicles":      {"tr": "Araçlar",                       "en": "Vehicles"},
    "cust_vehicle":       {"tr": "Araç",                          "en": "Vehicle"},
    "cust_registration":  {"tr": "Kayıt",                         "en": "Registration"},
    "cust_status":        {"tr": "Durum",                         "en": "Status"},
    "cust_personal":      {"tr": "Kişisel",                       "en": "Personal"},
    "cust_email":         {"tr": "E-posta",                       "en": "Email"},
    "cust_phone":         {"tr": "Telefon",                       "en": "Phone"},
    "cust_new_record":    {"tr": "Yeni müşteri kaydı oluştur",    "en": "Create a new customer record"},
    "cust_personal_info": {"tr": "Kişisel Bilgiler",              "en": "Personal Information"},
    "cust_vehicle_info":  {"tr": "Araç Bilgisi",                  "en": "Vehicle Information"},
    "cust_extra_info":    {"tr": "Ek Bilgiler",                   "en": "Additional Information"},
    "cust_first_name":    {"tr": "Ad",                            "en": "First Name"},
    "cust_last_name":     {"tr": "Soyad",                         "en": "Last Name"},
    "cust_tc_no":         {"tr": "T.C. Kimlik No",                "en": "National ID Number"},
    "cust_address":       {"tr": "Adres",                         "en": "Address"},
    "cust_notes":         {"tr": "Notlar",                        "en": "Notes"},
    "cust_portal_pass":   {"tr": "Portal Şifresi",                "en": "Portal Password"},
    "cust_optional":      {"tr": "opsiyonel",                     "en": "optional"},
    "cust_no_portal":     {"tr": "Boş bırakılırsa müşteri portalına giriş yapamaz.", "en": "If left blank, the customer cannot log in to the portal."},
    "cust_create_plate":  {"tr": "Müşteri oluşturulduğunda bu plaka otomatik araç olarak eklenir.", "en": "When the customer is created, this plate will be added automatically as a vehicle."},
    "cust_tc_rule":       {"tr": "11 haneli, 0 ile başlamaz",     "en": "11 digits, cannot start with 0"},
    "cust_update":        {"tr": "Güncelle",                      "en": "Update"},
    "cust_cancel":        {"tr": "İptal",                         "en": "Cancel"},
    "cust_no_results":    {"tr": "Arama sonucu bulunamadı.",       "en": "No search results found."},
    "cust_no_customers":  {"tr": "Henüz kayıtlı müşteri yok.",    "en": "No customers registered yet."},
    "cust_delete_confirm": {
        "tr": "{name} adlı müşteriyi kalıcı olarak silmek istediğinizden emin misiniz?\n\nBu işlem geri alınamaz!",
        "en": "Are you sure you want to permanently delete customer {name}?\n\nThis action cannot be undone!",
    },
    "cust_delete_confirm_full": {
        "tr": "{name} adlı müşteriyi ve tüm araç/abonelik kayıtlarını kalıcı olarak silmek istediğinizden emin misiniz?\n\nBu işlem GERİ ALINAMAZ!",
        "en": "Are you sure you want to permanently delete customer {name} and all vehicle/subscription records?\n\nThis action CANNOT be undone!",
    },
    # ── Vehicles ─────────────────────────────────────────────────────
    "veh_title":          {"tr": "Araçlar",                       "en": "Vehicles"},
    "veh_new":            {"tr": "Araç Ekle",                     "en": "Add Vehicle"},
    "veh_edit":           {"tr": "Araç Düzenle",                  "en": "Edit Vehicle"},
    "veh_search":         {"tr": "Plaka ara...",                  "en": "Search plate..."},
    "veh_plate":          {"tr": "Plaka",                         "en": "Plate"},
    "veh_no_results":     {"tr": "Arama sonucu bulunamadı.",       "en": "No search results found."},
    "veh_no_vehicles":    {"tr": "Henüz kayıtlı araç yok.",       "en": "No vehicles registered yet."},
    # ── Subscriptions ────────────────────────────────────────────────
    "sub_new":            {"tr": "Yeni Abonelik",                 "en": "New Subscription"},
    "sub_sell":           {"tr": "Abonelik Sat",                  "en": "Sell Subscription"},
    "sub_plans_page":     {"tr": "Abonelik Planları",             "en": "Subscription Plans"},
    "sub_active":         {"tr": "AKTİF",                         "en": "ACTIVE"},
    "sub_soon_expire":    {"tr": "G KALDI",                       "en": "D LEFT"},
    "sub_pending_payment":{"tr": "ÖDEME BEKLİYOR",                "en": "PAYMENT PENDING"},
    "sub_cancelled":      {"tr": "İPTAL",                         "en": "CANCELLED"},
    "sub_expired":        {"tr": "SÜRESİ DOLDU",                  "en": "EXPIRED"},
    "sub_no_records":     {"tr": "Henüz abonelik kaydı yok.",     "en": "No subscription records yet."},
    # ── Sessions ─────────────────────────────────────────────────────
    "ses_title":          {"tr": "Oturum Geçmişi",                "en": "Session History"},
    "ses_entry":          {"tr": "Giriş",                         "en": "Entry"},
    # ── Status ───────────────────────────────────────────────────────
    "status_active":      {"tr": "Aktif",                         "en": "Active"},
    # ── Portal / Customer-facing ─────────────────────────────────────
    "portal_inside_badge":    {"tr": "İÇERİDE",                   "en": "INSIDE"},
    "portal_exited_badge":    {"tr": "ÇIKTI",                     "en": "EXITED"},
    "portal_no_entries":      {"tr": "Henüz giriş kaydınız yok.", "en": "You do not have any entry record yet."},
    "portal_my_sessions":     {"tr": "Giriş Geçmişim",            "en": "Entry History"},
    "portal_my_subs":         {"tr": "Aboneliklerim",             "en": "My Subscriptions"},
    "portal_add_vehicle":     {"tr": "Araç Ekle",                 "en": "Add Vehicle"},
    "portal_payment":         {"tr": "Ödeme",                     "en": "Payment"},
    "portal_payment_success": {"tr": "Ödeme Başarılı!",           "en": "Payment Successful!"},
    # ── Landing / Navigation ─────────────────────────────────────────
    "landing_plate":      {"tr": "Plaka Sorgula",                 "en": "Plate Query"},
    "nav_debts":          {"tr": "Borçlar",                       "en": "Debts"},
    # ── Errors ───────────────────────────────────────────────────────
    "err.auth_required": {
        "tr": "Giris yapmaniz gerekiyor.",
        "en": "You need to sign in.",
    },
    "err.forbidden": {
        "tr": "Bu islem icin yetkiniz yok.",
        "en": "You do not have permission for this action.",
    },
    "err.not_found": {
        "tr": "Endpoint bulunamadi.",
        "en": "Endpoint not found.",
    },
    "err.server": {
        "tr": "Sunucu hatasi.",
        "en": "Server error.",
    },
    "err.invalid_or_expired_token": {
        "tr": "Oturum suresi dolmus veya gecersiz token.",
        "en": "Session expired or token is invalid.",
    },
    "err.invalid_token": {
        "tr": "Gecersiz token.",
        "en": "Invalid token.",
    },
    "err.user_not_found": {
        "tr": "Kullanici bulunamadi.",
        "en": "User not found.",
    },
    "err.customer_login_required": {
        "tr": "Musteri girisi gereklidir.",
        "en": "Customer login is required.",
    },
    "err.customer_not_found": {
        "tr": "Musteri bulunamadi.",
        "en": "Customer not found.",
    },
    "auth.invalid_credentials": {
        "tr": "E-posta veya sifre yanlis.",
        "en": "Email or password is incorrect.",
    },
    "auth.email_exists": {
        "tr": "Bu e-posta adresi zaten kayitli.",
        "en": "This email address is already registered.",
    },
}


def normalize_lang(value: str | None) -> str:
    if not value:
        return DEFAULT_LANG
    lowered = value.strip().lower()
    if lowered.startswith("tr"):
        return "tr"
    if lowered.startswith("en"):
        return "en"
    return DEFAULT_LANG


def _pick_lang_from_accept_language(header: str | None) -> str:
    if not header:
        return DEFAULT_LANG
    for part in header.split(","):
        raw_lang = part.split(";")[0].strip()
        lang = normalize_lang(raw_lang)
        if lang in SUPPORTED_LANGS:
            return lang
    return DEFAULT_LANG


def resolve_lang(request: Request) -> str:
    query_lang = normalize_lang(request.query_params.get("lang")) if "lang" in request.query_params else None
    if query_lang:
        return query_lang

    cookie_lang = normalize_lang(request.cookies.get(LANG_COOKIE_NAME))
    if cookie_lang in SUPPORTED_LANGS:
        return cookie_lang

    return _pick_lang_from_accept_language(request.headers.get("accept-language"))


def get_request_lang(request: Request) -> str:
    return normalize_lang(getattr(request.state, "lang", None) or resolve_lang(request))


def translate(key: str, lang: str | None = None, **kwargs: Any) -> str:
    target_lang = normalize_lang(lang)
    value = TRANSLATIONS.get(key, {}).get(target_lang) or TRANSLATIONS.get(key, {}).get(DEFAULT_LANG) or key
    if kwargs:
        try:
            return value.format(**kwargs)
        except Exception:
            return value
    return value


def i18n_context_processor(request: Request) -> dict[str, Any]:
    lang = get_request_lang(request)

    def _t(key: str, **kwargs: Any) -> str:
        return translate(key, lang=lang, **kwargs)

    return {
        "lang": lang,
        "t": _t,
        "supported_langs": SUPPORTED_LANGS,
    }


def get_templates(directory: str | Path) -> Jinja2Templates:
    templates = Jinja2Templates(
        directory=str(directory),
        context_processors=[i18n_context_processor],
    )

    def _global_t(key: str, lang: str = DEFAULT_LANG, **kwargs: Any) -> str:
        return translate(key, lang=lang, **kwargs)

    templates.env.globals["translate"] = _global_t
    return templates
