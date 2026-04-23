/**
 * OtoparkPro — Alpine.js Global Store
 * Theme (dark/light) + i18n (TR/EN)
 */

const TRANSLATIONS = {
  tr: {
    // Navigation
    nav_dashboard:     "Dashboard",
    nav_camera:        "Kamera",
    nav_cam_entry:     "Giriş Kamerası",
    nav_cam_exit:      "Çıkış Kamerası",
    nav_customers:     "Müşteriler",
    nav_vehicles:      "Araçlar",
    nav_subscriptions: "Abonelikler",
    nav_sessions:      "Oturumlar",
    nav_reports:       "Raporlar",
    nav_users:         "Kullanıcılar",
    nav_logout:        "Çıkış Yap",
    nav_management:    "Yönetim",
    // Header
    header_search:     "Plaka, müşteri ara...",
    // Common buttons
    btn_save:          "Kaydet",
    btn_cancel:        "İptal",
    btn_edit:          "Düzenle",
    btn_delete:        "Sil",
    btn_detail:        "Detay",
    btn_new:           "Yeni",
    btn_back:          "Geri",
    btn_update:        "Güncelle",
    btn_confirm:       "Onayla",
    btn_search:        "Ara",
    // Status
    status_active:     "Aktif",
    status_passive:    "Pasif",
    status_inside:     "İçeride",
    status_exited:     "Çıktı",
    status_expired:    "Süresi Doldu",
    status_cancelled:  "İptal",
    status_pending:    "Bekliyor",
    // System
    sys_health:        "Sistem Durumu",
    sys_ok:            "Tüm sistemler çalışıyor",
    // Login page
    login_title:       "Giriş Yap",
    login_email:       "E-posta",
    login_password:    "Şifre",
    login_btn:         "Giriş",
    login_customer:    "Müşteri Girişi",
    // Dashboard
    dash_welcome:      "Hoş geldiniz",
    dash_active:       "İçeride",
    dash_capacity:     "Kapasite",
    dash_available:    "Boş",
    // Customers
    cust_title:        "Müşteriler",
    cust_new:          "Yeni Müşteri",
    cust_search:       "İsim, telefon ara...",
    cust_name:         "Müşteri",
    cust_phone:        "Telefon",
    cust_email:        "E-posta",
    cust_vehicle:      "Araç",
    // Vehicles
    veh_title:         "Araçlar",
    veh_new:           "Araç Ekle",
    veh_search:        "Plaka ara...",
    veh_plate:         "Plaka",
    veh_type:          "Araç",
    veh_owner:         "Müşteri",
    veh_sub:           "Abonelik",
    // Subscriptions
    sub_title:         "Abonelikler",
    sub_new:           "Yeni Abonelik",
    sub_sell:          "Abonelik Sat",
    sub_plans:         "Planlar",
    sub_plan:          "Plan",
    sub_start:         "Başlangıç",
    sub_end:           "Bitiş",
    sub_status:        "Durum",
    // Sessions
    ses_title:         "Oturum Geçmişi",
    ses_entry:         "Giriş",
    ses_exit:          "Çıkış",
    ses_duration:      "Süre",
    // Payment
    pay_title:         "Ödeme",
    pay_summary:       "Sipariş Özeti",
    pay_card:          "Kart Numarası",
    pay_name:          "Kart Üzerindeki İsim",
    pay_expiry:        "Son Kullanma",
    pay_cvv:           "CVV",
    pay_btn:           "Öde",
    pay_success:       "Ödeme Başarılı!",
    // Camera
    cam_title:         "Canlı Kamera",
    cam_entry:         "Giriş",
    cam_exit:          "Çıkış",
    cam_occupancy:     "Doluluk",
    // Admin
    adm_title:         "Admin Dashboard",
    adm_users:         "Kullanıcılar",
    adm_reports:       "Raporlar",
    adm_config:        "Konfigürasyon",
    // Portal
    portal_my_vehicles:    "Araçlarım",
    portal_my_subs:        "Aboneliklerim",
    portal_my_sessions:    "Giriş Geçmişim",
    portal_days_left:      "gün kaldı",
    portal_no_active_sub:  "Aktif abonelik yok",
    // Page labels
    dash_kasiyer_title:    "Kasiyer Paneli",
    dash_admin_title:      "Admin Dashboard",
    lbl_currently_inside:  "Şu An İçeride",
    lbl_recent_activity:   "Son Aktiviteler",
    lbl_view_all:          "Tüm Geçmiş",
    lbl_view_all_short:    "Tümünü Gör",
    lbl_plate:             "Plaka",
    lbl_vehicle:           "Araç",
    lbl_entry_time:        "Giriş Saati",
    lbl_exit_time:         "Çıkış Saati",
    lbl_duration:          "Süre",
    lbl_action:            "İşlem",
    lbl_status:            "Durum",
    lbl_plan:              "Plan",
    lbl_start:             "Başlangıç",
    lbl_end:               "Bitiş",
    lbl_customer:          "Müşteri",
    lbl_occupancy:         "Doluluk",
    lbl_records:           "kayıt",
    lbl_vehicles_reg:      "kayıtlı araç",
    lbl_sub_records:       "abonelik kaydı",
    lbl_today_entry:       "Bugün Giriş",
    lbl_expiring:          "Süresi Dolacak",
    lbl_customers:         "Müşteri",
    lbl_vehicles:          "Araç",
    lbl_active_subs:       "Aktif Abonelik",
  },
  en: {
    // Navigation
    nav_dashboard:     "Dashboard",
    nav_camera:        "Camera",
    nav_cam_entry:     "Entry Camera",
    nav_cam_exit:      "Exit Camera",
    nav_customers:     "Customers",
    nav_vehicles:      "Vehicles",
    nav_subscriptions: "Subscriptions",
    nav_sessions:      "Sessions",
    nav_reports:       "Reports",
    nav_users:         "Users",
    nav_logout:        "Log Out",
    nav_management:    "Management",
    // Header
    header_search:     "Search plate, customer...",
    // Common buttons
    btn_save:          "Save",
    btn_cancel:        "Cancel",
    btn_edit:          "Edit",
    btn_delete:        "Delete",
    btn_detail:        "Detail",
    btn_new:           "New",
    btn_back:          "Back",
    btn_update:        "Update",
    btn_confirm:       "Confirm",
    btn_search:        "Search",
    // Status
    status_active:     "Active",
    status_passive:    "Inactive",
    status_inside:     "Inside",
    status_exited:     "Exited",
    status_expired:    "Expired",
    status_cancelled:  "Cancelled",
    status_pending:    "Pending",
    // System
    sys_health:        "System Health",
    sys_ok:            "All systems operational",
    // Login page
    login_title:       "Sign In",
    login_email:       "Email",
    login_password:    "Password",
    login_btn:         "Sign In",
    login_customer:    "Customer Login",
    // Dashboard
    dash_welcome:      "Welcome",
    dash_active:       "Inside",
    dash_capacity:     "Capacity",
    dash_available:    "Available",
    // Customers
    cust_title:        "Customers",
    cust_new:          "New Customer",
    cust_search:       "Search name, phone...",
    cust_name:         "Customer",
    cust_phone:        "Phone",
    cust_email:        "Email",
    cust_vehicle:      "Vehicle",
    // Vehicles
    veh_title:         "Vehicles",
    veh_new:           "Add Vehicle",
    veh_search:        "Search plate...",
    veh_plate:         "Plate",
    veh_type:          "Vehicle",
    veh_owner:         "Customer",
    veh_sub:           "Subscription",
    // Subscriptions
    sub_title:         "Subscriptions",
    sub_new:           "New Subscription",
    sub_sell:          "Sell Subscription",
    sub_plans:         "Plans",
    sub_plan:          "Plan",
    sub_start:         "Start",
    sub_end:           "End",
    sub_status:        "Status",
    // Sessions
    ses_title:         "Session History",
    ses_entry:         "Entry",
    ses_exit:          "Exit",
    ses_duration:      "Duration",
    // Payment
    pay_title:         "Payment",
    pay_summary:       "Order Summary",
    pay_card:          "Card Number",
    pay_name:          "Cardholder Name",
    pay_expiry:        "Expiry",
    pay_cvv:           "CVV",
    pay_btn:           "Pay",
    pay_success:       "Payment Successful!",
    // Camera
    cam_title:         "Live Camera",
    cam_entry:         "Entry",
    cam_exit:          "Exit",
    cam_occupancy:     "Occupancy",
    // Admin
    adm_title:         "Admin Dashboard",
    adm_users:         "Users",
    adm_reports:       "Reports",
    adm_config:        "Configuration",
    // Portal
    portal_my_vehicles:    "My Vehicles",
    portal_my_subs:        "My Subscriptions",
    portal_my_sessions:    "Entry History",
    portal_days_left:      "days left",
    portal_no_active_sub:  "No active subscription",
    // Page labels
    dash_kasiyer_title:    "Cashier Panel",
    dash_admin_title:      "Admin Dashboard",
    lbl_currently_inside:  "Currently Inside",
    lbl_recent_activity:   "Recent Activity",
    lbl_view_all:          "View All",
    lbl_view_all_short:    "View All",
    lbl_plate:             "Plate",
    lbl_vehicle:           "Vehicle",
    lbl_entry_time:        "Entry Time",
    lbl_exit_time:         "Exit Time",
    lbl_duration:          "Duration",
    lbl_action:            "Action",
    lbl_status:            "Status",
    lbl_plan:              "Plan",
    lbl_start:             "Start",
    lbl_end:               "End",
    lbl_customer:          "Customer",
    lbl_occupancy:         "Occupancy",
    lbl_records:           "records",
    lbl_vehicles_reg:      "registered vehicles",
    lbl_sub_records:       "subscription records",
    lbl_today_entry:       "Today's Entries",
    lbl_expiring:          "Expiring Soon",
    lbl_customers:         "Customers",
    lbl_vehicles:          "Vehicles",
    lbl_active_subs:       "Active Subscriptions",
  }
};

document.addEventListener("alpine:init", () => {
  Alpine.store("app", {
    // ── Theme ─────────────────────────────────────────────────────
    theme: localStorage.getItem("theme") || "dark",

    get isDark() { return this.theme === "dark"; },

    toggleTheme() {
      this.theme = this.isDark ? "light" : "dark";
      localStorage.setItem("theme", this.theme);
      this._applyTheme();
    },

    _applyTheme() {
      if (this.isDark) {
        document.documentElement.classList.add("dark");
        document.documentElement.classList.remove("light");
        document.documentElement.style.colorScheme = "dark";
      } else {
        document.documentElement.classList.remove("dark");
        document.documentElement.classList.add("light");
        document.documentElement.style.colorScheme = "light";
      }
    },

    // ── Language ──────────────────────────────────────────────────
    lang: localStorage.getItem("lang") || "tr",

    get isEN() { return this.lang === "en"; },

    toggleLang() {
      this.lang = this.isEN ? "tr" : "en";
      localStorage.setItem("lang", this.lang);
    },

    t(key) {
      return TRANSLATIONS[this.lang]?.[key] ?? TRANSLATIONS["tr"]?.[key] ?? key;
    },

    // ── Init ──────────────────────────────────────────────────────
    init() {
      this._applyTheme();
    }
  });
});
