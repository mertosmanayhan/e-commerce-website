package com.datapulse.ecommerce.seed;

import com.datapulse.ecommerce.entity.*;
import com.datapulse.ecommerce.entity.enums.OrderStatus;
import com.datapulse.ecommerce.entity.enums.Role;
import com.datapulse.ecommerce.entity.enums.ShipmentStatus;
import com.datapulse.ecommerce.repository.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;

@Component
public class DataSeeder implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(DataSeeder.class);

    private final UserRepository userRepo;
    private final StoreRepository storeRepo;
    private final CategoryRepository catRepo;
    private final ProductRepository prodRepo;
    private final OrderRepository orderRepo;
    private final ReviewRepository reviewRepo;
    private final ShipmentRepository shipRepo;
    private final CustomerProfileRepository cpRepo;
    private final OrderItemRepository orderItemRepo;
    private final PasswordEncoder passwordEncoder;

    public DataSeeder(UserRepository ur, StoreRepository sr, CategoryRepository cr,
                      ProductRepository pr, OrderRepository or, ReviewRepository rr,
                      ShipmentRepository shr, CustomerProfileRepository cpr,
                      OrderItemRepository oir, PasswordEncoder pe) {
        this.userRepo = ur; this.storeRepo = sr; this.catRepo = cr; this.prodRepo = pr;
        this.orderRepo = or; this.reviewRepo = rr; this.shipRepo = shr; this.cpRepo = cpr;
        this.orderItemRepo = oir; this.passwordEncoder = pe;
    }

    @Override
    @Transactional
    public void run(String... args) {
        if (userRepo.count() > 0) { log.info("DB already seeded — skipping."); return; }
        log.info("=== DataPulse Seed başlıyor... ===");

        // ── 1. KULLANICILAR ──────────────────────────────────────────────────
        User admin = save(user("DataPulse Admin",    "admin@datapulse.com",  "123456", Role.ADMIN,       "Male",   35, "Istanbul"));
        User corp1 = save(user("Ahmet Yılmaz",       "ahmet@datapulse.com",  "123456", Role.CORPORATE,   "Male",   42, "Ankara"));
        User corp2 = save(user("Elif Kaya",          "elif@datapulse.com",   "123456", Role.CORPORATE,   "Female", 38, "Izmir"));
        User ind1  = save(user("Mehmet Demir",       "mehmet@gmail.com",     "123456", Role.INDIVIDUAL,  "Male",   28, "Istanbul"));
        User ind2  = save(user("Zeynep Çelik",       "zeynep@gmail.com",     "123456", Role.INDIVIDUAL,  "Female", 24, "Bursa"));
        User ind3  = save(user("Can Özkan",          "can@gmail.com",        "123456", Role.INDIVIDUAL,  "Male",   31, "Antalya"));
        User ind4  = save(user("Selin Arslan",       "selin@gmail.com",      "123456", Role.INDIVIDUAL,  "Female", 22, "Eskişehir"));
        User ind5  = save(user("Burak Şahin",        "burak@gmail.com",      "123456", Role.INDIVIDUAL,  "Male",   27, "Konya"));

        cpRepo.save(CustomerProfile.builder().user(ind1).membershipType("Gold")  .totalSpend(BigDecimal.valueOf(4500)).itemsPurchased(12).avgRating(4.5).discountApplied(true) .satisfactionLevel("Satisfied").build());
        cpRepo.save(CustomerProfile.builder().user(ind2).membershipType("Silver").totalSpend(BigDecimal.valueOf(1200)).itemsPurchased(5) .avgRating(4.8).discountApplied(false).satisfactionLevel("Very Satisfied").build());
        cpRepo.save(CustomerProfile.builder().user(ind3).membershipType("Bronze").totalSpend(BigDecimal.valueOf(350)) .itemsPurchased(2) .avgRating(3.5).discountApplied(false).satisfactionLevel("Neutral").build());

        // ── 2. KATEGORİLER ──────────────────────────────────────────────────
        Category electronics = saveCat("Elektronik");
        Category clothing    = saveCat("Giyim & Moda");
        Category books       = saveCat("Kitap & Kırtasiye");
        Category sports      = saveCat("Spor & Outdoor");
        Category home        = saveCat("Ev & Yaşam");
        Category beauty      = saveCat("Kozmetik & Bakım");
        Category toys        = saveCat("Oyuncak & Hobi");
        Category food        = saveCat("Gıda & İçecek");

        // ── 3. MAĞAZALAR ────────────────────────────────────────────────────
        Store techStore  = saveStore("TechStore",  "En güncel teknoloji ürünleri",   corp1);
        Store fashionHub = saveStore("FashionHub", "Trend moda ve giyim mağazası",    corp2);

        // ── 4. ÜRÜNLER ──────────────────────────────────────────────────────
        List<Product> products = new ArrayList<>();

        // Elektronik
        products.add(prod("iPhone 15 Pro",          "Apple'ın amiral gemisi. 48MP kamera, A17 Pro çip, titanyum gövde.",           "SKU-E001", 54999, 25, electronics, techStore,  "https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=400", 4.8, 312));
        products.add(prod("Samsung Galaxy S24",     "6.2\" Dynamic AMOLED, Snapdragon 8 Gen 3, 50MP üçlü kamera.",                "SKU-E002", 42999, 18, electronics, techStore,  "https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?w=400", 4.7, 278));
        products.add(prod("MacBook Air M3",         "13.6\" Liquid Retina, 18 saate kadar pil, M3 çip, 8GB RAM.",                 "SKU-E003", 89999, 12, electronics, techStore,  "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400", 4.9, 445));
        products.add(prod("iPad Pro 12.9\"",        "M4 çipli iPad Pro, ProMotion ekran, Apple Pencil Pro desteği.",              "SKU-E004", 44999, 20, electronics, techStore,  "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400", 4.7, 198));
        products.add(prod("Sony WH-1000XM5",        "Endüstri lideri gürültü önleme, 30 saat pil, Multipoint bağlantı.",         "SKU-E005", 12999, 40, electronics, techStore,  "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400", 4.8, 567));
        products.add(prod("Apple Watch Series 9",   "Always-On Retina, çift dokunuş özelliği, gelişmiş sağlık takibi.",          "SKU-E006", 17999, 30, electronics, techStore,  "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400", 4.6, 234));
        products.add(prod("LG OLED C3 55\"",        "55\" OLED 4K 120Hz, Dolby Vision & Atmos, webOS 23.",                       "SKU-E007", 34999, 8,  electronics, techStore,  "https://images.unsplash.com/photo-1593784991095-a205069470b6?w=400", 4.9, 123));
        products.add(prod("DJI Mini 4 Pro",         "4K/60fps drone, obstacle sensing, 34 dk uçuş süresi.",                      "SKU-E008", 24999, 15, electronics, techStore,  "https://images.unsplash.com/photo-1473968512647-3e447244af8f?w=400", 4.7, 89));
        products.add(prod("Logitech MX Master 3S",  "8K DPI kablosuz fare, MagSpeed kaydırma, ergonomik tasarım.",               "SKU-E009",  2499, 60, electronics, techStore,  "https://images.unsplash.com/photo-1527814050087-3793815479db?w=400", 4.8, 678));
        products.add(prod("Samsung 980 Pro 1TB",    "NVMe M.2 SSD, 7000MB/s okuma, PCIe 4.0.",                                   "SKU-E010",  3499, 45, electronics, techStore,  "https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?w=400", 4.7, 345));

        // Giyim
        products.add(prod("Nike Air Force 1",       "Klasik deri sneaker, beyaz, her kombine uyar.",                              "SKU-G001",  3799, 50, clothing, fashionHub, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400", 4.7, 892));
        products.add(prod("Levi's 501 Original",    "Düz kesim, button-fly, %100 denim.",                                        "SKU-G002",  2299, 35, clothing, fashionHub, "https://images.unsplash.com/photo-1542272604-787c3835535d?w=400", 4.6, 567));
        products.add(prod("Zara Blazer",            "Slim fit, oversize yaka, kış koleksiyonu.",                                  "SKU-G003",  1899, 28, clothing, fashionHub, "https://images.unsplash.com/photo-1594938298603-c8148c4b2d7d?w=400", 4.5, 234));
        products.add(prod("Adidas Ultraboost 22",   "Running ayakkabı, Boost teknolojisi, Continental taban.",                    "SKU-G004",  4599, 40, clothing, fashionHub, "https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=400", 4.8, 445));
        products.add(prod("Tommy Hilfiger Polo",    "Slim fit pike kumaş polo, 5 renk seçeneği.",                                 "SKU-G005",  1299, 55, clothing, fashionHub, "https://images.unsplash.com/photo-1586363104862-3a5e2ab60d99?w=400", 4.4, 312));
        products.add(prod("Mango Midi Elbise",      "V yaka, çiçek desenli, yazlık koleksiyon.",                                  "SKU-G006",   899, 42, clothing, fashionHub, "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=400", 4.5, 178));
        products.add(prod("H&M Trençkot",           "Çift sıra düğmeli, kemer detaylı, oversize.",                                "SKU-G007",  2799, 22, clothing, fashionHub, "https://images.unsplash.com/photo-1539533018447-63fcce2678e3?w=400", 4.3, 145));

        // Kitap
        products.add(prod("Atomic Habits",          "James Clear - Küçük değişimlerin büyük sonuçları.",                         "SKU-K001",   249, 100, books, techStore, "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=400", 4.9, 1234));
        products.add(prod("Dune",                   "Frank Herbert - Bilim kurgunun başyapıtı, 896 sayfa.",                       "SKU-K002",   189, 75,  books, techStore, "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400", 4.8, 789));
        products.add(prod("Python Programlama",     "Sıfırdan ileri seviyeye, 500+ alıştırma.",                                   "SKU-K003",   349, 60,  books, techStore, "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?w=400", 4.7, 456));
        products.add(prod("Rich Dad Poor Dad",      "Robert Kiyosaki - Finansal özgürlük yolculuğu.",                             "SKU-K004",   199, 90,  books, techStore, "https://images.unsplash.com/photo-1553729459-efe14ef6055d?w=400", 4.6, 678));

        // Spor
        products.add(prod("Garmin Forerunner 955",  "GPS koşu saati, harita desteği, 15 gün pil ömrü.",                          "SKU-S001", 14999, 20, sports, techStore,  "https://images.unsplash.com/photo-1434494878577-86c23bcb06b9?w=400", 4.7, 189));
        products.add(prod("Yoga Mat Pro",           "6mm TPE ekstra kalın, kaymaz yüzey, %100 çevre dostu.",                      "SKU-S002",   699, 65, sports, fashionHub, "https://images.unsplash.com/photo-1601925228869-41a0f3e8a75b?w=400", 4.6, 345));
        products.add(prod("Fitbit Charge 6",        "Kalp ritmi, uyku analizi, 7 gün pil.",                                       "SKU-S003",  4999, 35, sports, techStore,  "https://images.unsplash.com/photo-1575311373937-040b8e1fd5b6?w=400", 4.5, 234));
        products.add(prod("Dambıl Set 10kg",        "Kauçuk kaplı 5+5 dambıl, ergonomik tutamak.",                                "SKU-S004",  1299, 30, sports, fashionHub, "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=400", 4.7, 178));

        // Ev & Yaşam
        products.add(prod("Dyson V15 Detect",       "Lazer tozlu zemin tespiti, 60 dk çalışma, HEPA filtre.",                     "SKU-H001", 18999, 10, home, techStore,  "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400", 4.8, 267));
        products.add(prod("Nespresso Vertuo",       "Kapsül kahve makinesi, 5 fincan boyutu, 15 bar.",                             "SKU-H002",  4999, 25, home, techStore,  "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=400", 4.7, 445));
        products.add(prod("Philips Hue Starter Kit","4x akıllı ampul + köprü, 16 milyon renk.",                                   "SKU-H003",  3299, 30, home, techStore,  "https://images.unsplash.com/photo-1565814329452-e1efa11c5b89?w=400", 4.6, 234));
        products.add(prod("Nevresim Takımı Bambu",  "5 parça, 400 iplik, anti-alerjik, çift kişilik.",                             "SKU-H004",  1299, 40, home, fashionHub, "https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?w=400", 4.5, 189));

        // Kozmetik
        products.add(prod("The Ordinary Niacinamide","10% Niacinamide + 1% Zinc, gözenek bakımı, 30ml.",                         "SKU-C001",   399, 80, beauty, fashionHub, "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=400", 4.7, 567));
        products.add(prod("Cerave Nemlendirici",    "Ceramide & hyaluronik asit, yüz & vücut, 354ml.",                            "SKU-C002",   549, 70, beauty, fashionHub, "https://images.unsplash.com/photo-1556228453-efd6c1ff04f6?w=400", 4.8, 789));
        products.add(prod("La Roche SPF50+",        "Güneş koruyucu UVA/UVB, hassas cilt, 50ml.",                                 "SKU-C003",   649, 55, beauty, fashionHub, "https://images.unsplash.com/photo-1598300042247-d088f8ab3a91?w=400", 4.9, 456));
        products.add(prod("Dyson Airwrap",          "Saç şekillendirici, 6 aparatlı, koaksiyel akış teknolojisi.",                "SKU-C004", 14999, 12, beauty, fashionHub, "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=400", 4.7, 234));

        // Oyuncak
        products.add(prod("LEGO Technic Bugatti",   "3599 parça, 1:8 ölçek, çalışan dişliler, 18+ yaş.",                         "SKU-O001", 12999, 15, toys, techStore,  "https://images.unsplash.com/photo-1587654780291-39c9404d746b?w=400", 4.9, 178));
        products.add(prod("PS5 DualSense",          "Haptic feedback, adaptive trigger, built-in mikrofon.",                      "SKU-O002",  2799, 20, toys, techStore,  "https://images.unsplash.com/photo-1606813907291-d86efa9b94db?w=400", 4.8, 567));
        products.add(prod("Nintendo Switch OLED",   "7\" OLED ekran, TV & taşınabilir mod.",                                      "SKU-O003", 16999, 10, toys, techStore,  "https://images.unsplash.com/photo-1578303512597-81e6cc155b3e?w=400", 4.8, 345));

        // Gıda
        products.add(prod("Nescafé Gold 250g",      "Öğütülmüş Arabica kahve, zengin aroma, altın kavurma.",                     "SKU-F001",   349, 100, food, techStore,  "https://images.unsplash.com/photo-1512568400610-62da28bc8a13?w=400", 4.6, 456));
        products.add(prod("Whey Protein Çikolata",  "2kg, %80 protein, 67 servis, çikolata aromalı.",                             "SKU-F002",  1999, 30, food, fashionHub, "https://images.unsplash.com/photo-1593095948071-474c5cc2989d?w=400", 4.7, 345));
        products.add(prod("Organik Yeşil Çay",      "50 poşet, Japon matcha karışımı, antioksidan.",                              "SKU-F003",   299, 80, food, fashionHub, "https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=400", 4.5, 234));

        prodRepo.saveAll(products);
        log.info("✓ {} ürün eklendi", products.size());

        // ── 5. SİPARİŞLER (Son 30 Gün) ──────────────────────────────────────
        Random rnd = new Random(42L);
        List<User> buyers = List.of(ind1, ind2, ind3, ind4, ind5);
        List<OrderStatus> statuses = List.of(
            OrderStatus.DELIVERED, OrderStatus.DELIVERED, OrderStatus.DELIVERED,
            OrderStatus.SHIPPED, OrderStatus.PENDING, OrderStatus.CANCELLED
        );

        int orderCount = 0;
        for (int day = 29; day >= 0; day--) {
            int perDay = 2 + rnd.nextInt(5);
            for (int i = 0; i < perDay; i++) {
                User buyer   = buyers.get(rnd.nextInt(buyers.size()));
                int numItems = 1 + rnd.nextInt(3);
                List<Product> picked = pickRandom(products, numItems, rnd);

                Order order = new Order();
                order.setOrderNumber("ORD-" + String.format("%05d", ++orderCount));
                order.setUser(buyer);
                order.setStatus(statuses.get(rnd.nextInt(statuses.size())));
                order.setPaymentMethod(rnd.nextBoolean() ? "Kredi Kartı" : "Havale");
                order.setOrderDate(LocalDateTime.now().minusDays(day).minusHours(rnd.nextInt(18)));
                order.setTotalAmount(BigDecimal.ZERO); // nullable değil, sonra güncellenecek

                Order saved = orderRepo.save(order);
                BigDecimal total = BigDecimal.ZERO;
                for (Product p : picked) {
                    int qty = 1 + rnd.nextInt(2);
                    OrderItem item = new OrderItem();
                    item.setOrder(saved);
                    item.setProduct(p);
                    item.setQuantity(qty);
                    item.setUnitPrice(p.getPrice());
                    orderItemRepo.save(item);
                    total = total.add(p.getPrice().multiply(BigDecimal.valueOf(qty)));
                }
                saved.setTotalAmount(total);
                orderRepo.save(saved);
            }
        }
        log.info("✓ {} sipariş eklendi (30 günlük analitik verisi)", orderCount);

        // ── 6. YORUMLAR ──────────────────────────────────────────────────────
        Product sw = products.get(0); Product ear = products.get(4); Product kb = products.get(8);
        reviewRepo.saveAll(List.of(
            Review.builder().user(ind1).product(sw).starRating(5).reviewText("Harika bir telefon, kamera inanılmaz!").helpfulVotes(12).totalVotes(15).build(),
            Review.builder().user(ind2).product(sw).starRating(4).reviewText("Genel olarak çok iyi bir ürün.").helpfulVotes(8).totalVotes(10).build(),
            Review.builder().user(ind1).product(ear).starRating(5).reviewText("En iyi gürültü engelleme kulaklık!").helpfulVotes(20).totalVotes(22).build(),
            Review.builder().user(ind3).product(kb).starRating(4).reviewText("Kodlama için mükemmel.").helpfulVotes(5).totalVotes(7).build()
        ));

        log.info("=== Seed tamamlandı! ===");
        log.info("Demo hesaplar:");
        log.info("  Admin    : admin@datapulse.com / 123456");
        log.info("  Corporate: ahmet@datapulse.com / 123456");
        log.info("  Individual: mehmet@gmail.com / 123456");
    }

    // ── Yardımcılar ──────────────────────────────────────────────────────────

    private User user(String name, String email, String pass, Role role, String gender, int age, String city) {
        return User.builder().fullName(name).email(email).password(passwordEncoder.encode(pass))
            .role(role).gender(gender).age(age).city(city).country("Turkey").enabled(true).build();
    }
    private User save(User u) { return userRepo.save(u); }

    private Category saveCat(String name) {
        Category c = new Category(); c.setName(name); return catRepo.save(c);
    }

    private Store saveStore(String name, String desc, User owner) {
        Store s = new Store(); s.setName(name); s.setDescription(desc);
        s.setOwner(owner); s.setIsOpen(true); return storeRepo.save(s);
    }

    private Product prod(String name, String desc, String sku, double price, int stock,
                         Category cat, Store store, String img, double rating, int reviews) {
        return Product.builder().name(name).description(desc).sku(sku)
            .price(BigDecimal.valueOf(price)).stock(stock).category(cat).store(store)
            .imageUrl(img).rating(rating).reviewCount(reviews).build();
    }

    private <T> List<T> pickRandom(List<T> list, int n, Random rnd) {
        List<T> copy = new ArrayList<>(list);
        Collections.shuffle(copy, rnd);
        return copy.subList(0, Math.min(n, copy.size()));
    }
}
