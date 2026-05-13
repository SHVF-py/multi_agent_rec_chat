// ─── PRODUCT DATA ───
const laptops = [
  {
    id: 1,
    name: "HP EliteBook X360 1030 G7 | 13.3\" 1080p Display | i7 10th Gen 10610U | 32GB RAM 512GB SSD",
    price: 123000,
    oldPrice: 145000,
    badge: "Pre-Owned",
    badgeClass: "",
    specs: ["i7 10th Gen", "32GB RAM", "512GB SSD", "13.3\""],
    img: "https://hf-store.pk/wp-content/uploads/2024/02/WhatsApp-Image-2025-05-02-at-10.28.00-PM-700x542.jpeg",
    rating: 4.7,
    hasOptions: false,
    processor: "Intel Core i7-10610U",
    processorGen: "10th Gen",
    ram: "32GB DDR4",
    storage: "512GB NVMe SSD",
    display: "13.3\" FHD 1080p IPS Touch 2-in-1",
    os: "Windows 11 Pro",
    battery: "56Wh Li-ion",
    weight: "1.32 kg",
    condition: "Pre-Owned",
    sku: "LZ-001",
    description: "The HP EliteBook X360 1030 G7 is HP's premium ultra-slim business 2-in-1 convertible. Powered by the Intel Core i7-10610U vPro processor, it handles demanding workloads with ease.\n\nThe 13.3\" Full HD IPS touchscreen with a 360° hinge lets you switch between laptop, tablet, tent, and stand modes effortlessly. With 32GB DDR4 RAM and a 512GB NVMe SSD, multitasking is seamless and boot times are near-instant.\n\nBuilt to MIL-STD-810H military durability standards, this unit has been fully tested and inspected. It arrives in excellent pre-owned condition — ideal for executives, consultants, and power users.",
    tags: ["EliteBook", "2-in-1", "13 inch", "i7", "Touch", "vPro", "Pre-Owned"],
  },
  {
    id: 2,
    name: "HP ProBook 450 G9 | 15\" 1080P Display | i5 12th Gen 1245U | 16GB RAM 256GB SSD",
    price: 115000,
    oldPrice: 132000,
    badge: "Pre-Owned",
    badgeClass: "",
    specs: ["i5 12th Gen", "16GB RAM", "256GB SSD", "15\""],
    img: "https://hf-store.pk/wp-content/uploads/2025/04/PROBOOK-450-G7-1-700x525.jpg",
    rating: 4.3,
    hasOptions: false,
    processor: "Intel Core i5-1245U",
    processorGen: "12th Gen",
    ram: "16GB DDR4",
    storage: "256GB NVMe SSD",
    display: "15.6\" FHD 1080p IPS Anti-Glare",
    os: "Windows 11 Pro",
    battery: "45Wh Li-ion",
    weight: "1.74 kg",
    condition: "Pre-Owned",
    sku: "LZ-002",
    description: "The HP ProBook 450 G9 is a dependable 15.6\" business laptop powered by the Intel Core i5-1245U 12th Generation processor — delivering a significant performance boost over previous generations thanks to its hybrid efficiency architecture.\n\nEquipped with 16GB DDR4 RAM and a 256GB NVMe SSD, it handles everyday office tasks, video conferencing, and light creative work without breaking a sweat. The bright FHD IPS anti-glare display makes it comfortable for extended work sessions.\n\nThis pre-owned unit has been thoroughly tested and is in great working condition.",
    tags: ["ProBook", "15 inch", "i5", "12th Gen", "Pre-Owned"],
  },
  {
    id: 3,
    name: "HP ProBook 640 G9 | 14\" 1080P Display | i5 12th Gen 1245U | 16GB RAM 256GB SSD",
    price: 90000,
    oldPrice: 108000,
    badge: "Pre-Owned",
    badgeClass: "",
    specs: ["i5 12th Gen", "16GB RAM", "256GB SSD", "14\""],
    img: "https://hf-store.pk/wp-content/uploads/2025/04/PROBOOK-450-G7-1-400x300.jpg",
    rating: 4.2,
    hasOptions: false,
    processor: "Intel Core i5-1245U",
    processorGen: "12th Gen",
    ram: "16GB DDR4",
    storage: "256GB NVMe SSD",
    display: "14\" FHD 1080p IPS Anti-Glare",
    os: "Windows 11 Pro",
    battery: "45Wh Li-ion",
    weight: "1.59 kg",
    condition: "Pre-Owned",
    sku: "LZ-003",
    description: "The HP ProBook 640 G9 offers the perfect balance of portability and performance for modern professionals. At 14 inches and 1.59 kg, it's lighter and more compact than a 15\" laptop while retaining the same 12th Gen Intel Core i5-1245U power.\n\nThe FHD IPS anti-glare display delivers sharp, accurate visuals whether you're in the office or working outdoors. Paired with 16GB RAM and a 256GB NVMe SSD, this machine is snappy and reliable for daily business use.\n\nPre-owned and fully tested — an outstanding value for budget-conscious professionals.",
    tags: ["ProBook", "14 inch", "i5", "12th Gen", "Pre-Owned"],
  },
  {
    id: 4,
    name: "HP EliteBook 830 G7 | i5 10th Gen 10310U | 13\" 1080p Display | 8GB RAM 256GB SSD",
    price: 73000,
    oldPrice: 88000,
    badge: "Pre-Owned",
    badgeClass: "",
    specs: ["i5 10th Gen", "8GB RAM", "256GB SSD", "13\""],
    img: "https://hf-store.pk/wp-content/uploads/2023/07/WhatsApp-Image-2024-12-14-at-05.01.51_adf86389-e1734181491750-394x300.jpg",
    rating: 4.5,
    hasOptions: false,
    processor: "Intel Core i5-10310U",
    processorGen: "10th Gen",
    ram: "8GB DDR4",
    storage: "256GB NVMe SSD",
    display: "13.3\" FHD 1080p IPS Anti-Glare",
    os: "Windows 11 Pro",
    battery: "53Wh Li-ion",
    weight: "1.25 kg",
    condition: "Pre-Owned",
    sku: "LZ-004",
    description: "The HP EliteBook 830 G7 is one of the most portable yet powerful business ultrabooks in HP's lineup. Weighing just 1.25 kg, it's engineered for professionals who travel frequently without wanting to sacrifice performance.\n\nThe Intel Core i5-10310U vPro processor with 8GB DDR4 RAM handles enterprise workloads efficiently, while the 256GB NVMe SSD provides fast storage. The slim 13.3\" FHD IPS display is crisp and legible even in bright environments.\n\nThis pre-owned unit is in excellent condition and represents exceptional value for a premium ultrabook.",
    tags: ["EliteBook", "13 inch", "i5", "Ultrabook", "vPro", "Pre-Owned"],
  },
  {
    id: 5,
    name: "HP EliteBook x360 1030 G2 | 13.3\" 1080p | i5 7th Gen 7300U | 8GB RAM 512GB SSD",
    price: 68000,
    oldPrice: null,
    badge: "Pre-Owned",
    badgeClass: "",
    specs: ["i5 7th Gen", "8GB RAM", "512GB SSD", "13.3\""],
    img: "https://hf-store.pk/wp-content/uploads/2023/12/WhatsApp-Image-2023-12-13-at-3.05.37-AM-400x278.jpeg",
    rating: 4.4,
    hasOptions: false,
    processor: "Intel Core i5-7300U",
    processorGen: "7th Gen",
    ram: "8GB DDR3",
    storage: "512GB NVMe SSD",
    display: "13.3\" FHD 1080p IPS Touch 2-in-1",
    os: "Windows 11 Pro",
    battery: "57Wh Li-ion",
    weight: "1.40 kg",
    condition: "Pre-Owned",
    sku: "LZ-005",
    description: "The HP EliteBook x360 1030 G2 is a sleek and versatile 2-in-1 business laptop built for professionals who value flexibility. The 360° hinge design allows it to transform into a tablet, tent, or stand mode in seconds.\n\nPowered by the Intel Core i5-7300U with 8GB RAM and a large 512GB SSD, it offers solid performance for document editing, email, web browsing, and video calls. The 13.3\" FHD IPS touchscreen is bright and responsive.\n\nAn affordable entry into the premium EliteBook 2-in-1 experience — fully tested and ready to use.",
    tags: ["EliteBook", "2-in-1", "13 inch", "i5", "Touch", "Pre-Owned"],
  },
  {
    id: 6,
    name: "ZBook Firefly 14 G8 | 14\" 1080p | i5 11th Gen 1145G7 | 16GB RAM 256GB SSD",
    price: 93000,
    priceRange: "₨93,000",
    oldPrice: null,
    badge: "Pre-Owned",
    badgeClass: "",
    specs: ["i5 11th Gen", "16GB RAM", "256GB SSD", "14\""],
    img: "https://hf-store.pk/wp-content/uploads/2024/05/WhatsApp-Image-2024-05-13-at-5.26.20-AM-400x300.jpeg",
    rating: 4.6,
    hasOptions: true,
    processor: "Intel Core i5-1145G7",
    processorGen: "11th Gen",
    ram: "16GB DDR4",
    storage: "256GB NVMe SSD",
    display: "14\" FHD 1080p IPS Anti-Glare",
    os: "Windows 11 Pro",
    battery: "56Wh Li-ion",
    weight: "1.34 kg",
    condition: "Pre-Owned",
    sku: "LZ-006",
    description: "The HP ZBook Firefly 14 G8 is HP's lightest mobile workstation — combining workstation-class reliability with the portability of an ultrabook. The Intel Core i5-1145G7 with Intel Iris Xe graphics makes it suitable for CAD, data analysis, and creative work.\n\nAt just 1.34 kg, it's the go-to choice for engineers and designers who are constantly on the move. 16GB DDR4 RAM and a 256GB NVMe SSD ensure smooth performance across demanding applications.\n\nThis pre-owned unit is in great condition and includes multiple configuration options.",
    tags: ["ZBook", "Workstation", "14 inch", "i5", "11th Gen", "Pre-Owned"],
  },
  {
    id: 7,
    name: "HP ProBook 650 G8 | 15\" 1080P Display | i5 11th Gen | 16GB RAM 256GB SSD",
    price: 97000,
    oldPrice: 115000,
    badge: "Pre-Owned",
    badgeClass: "",
    specs: ["i5 11th Gen", "16GB RAM", "256GB SSD", "15\""],
    img: "https://hf-store.pk/wp-content/uploads/2025/04/HP-ProBook-640-G5-400x209.jpg",
    rating: 4.3,
    hasOptions: false,
    processor: "Intel Core i5-1135G7",
    processorGen: "11th Gen",
    ram: "16GB DDR4",
    storage: "256GB NVMe SSD",
    display: "15.6\" FHD 1080p IPS Anti-Glare",
    os: "Windows 11 Pro",
    battery: "45Wh Li-ion",
    weight: "1.78 kg",
    condition: "Pre-Owned",
    sku: "LZ-007",
    description: "The HP ProBook 650 G8 is a sturdy, reliable 15.6\" business laptop designed for enterprise use. Built around the Intel Core i5-1135G7 11th Gen processor with Intel Iris Xe Graphics, it delivers a solid leap in performance over prior generations.\n\nWith 16GB DDR4 RAM and a 256GB NVMe SSD, it comfortably runs multiple applications simultaneously. The large FHD IPS display is ideal for productivity, spreadsheets, and video calls.\n\nThis pre-owned unit has passed full diagnostic testing and is ready for deployment.",
    tags: ["ProBook", "15 inch", "i5", "11th Gen", "Pre-Owned"],
  },
  {
    id: 8,
    name: "HP EliteBook 650 G9 | 15\" 1080P | i5 12th Gen | 16GB RAM 256GB SSD",
    price: 123000,
    oldPrice: 140000,
    badge: "Pre-Owned",
    badgeClass: "",
    specs: ["i5 12th Gen", "16GB RAM", "256GB SSD", "15\""],
    img: "https://hf-store.pk/wp-content/uploads/2024/09/WhatsApp-Image-2024-09-13-at-5.21.57-AM-2-400x300.jpeg",
    rating: 4.5,
    hasOptions: false,
    processor: "Intel Core i5-1245U",
    processorGen: "12th Gen",
    ram: "16GB DDR4",
    storage: "256GB NVMe SSD",
    display: "15.6\" FHD 1080p IPS Anti-Glare",
    os: "Windows 11 Pro",
    battery: "51Wh Li-ion",
    weight: "1.78 kg",
    condition: "Pre-Owned",
    sku: "LZ-008",
    description: "The HP EliteBook 650 G9 brings the premium EliteBook experience to a larger 15.6\" form factor. The Intel Core i5-1245U 12th Gen processor with its hybrid efficiency architecture delivers excellent performance per watt.\n\nWith 16GB DDR4 RAM and a 256GB NVMe SSD, this machine breezes through office productivity, video conferencing, and light content creation. The FHD IPS anti-glare screen is easy on the eyes during long sessions.\n\nPre-owned and fully tested — a step up from the ProBook range for professionals who want EliteBook build quality.",
    tags: ["EliteBook", "15 inch", "i5", "12th Gen", "Pre-Owned"],
  },
  {
    id: 9,
    name: "HP Spectre X360 | 16\" 2K Display 2-in-1 | Intel Ultra Core 7 155H | 16GB DDR5 1TB Gen4 SSD",
    price: 317000,
    oldPrice: null,
    badge: "New",
    badgeClass: "new",
    specs: ["Ultra 7 155H", "16GB DDR5", "1TB SSD", "16\" 2K"],
    img: "https://hf-store.pk/wp-content/uploads/2024/09/1520a4ab-c5a4-4e94-9dcb-c257a2b419b3-400x295.jpg",
    rating: 4.8,
    hasOptions: false,
    processor: "Intel Core Ultra 7 155H",
    processorGen: "Meteor Lake (Core Ultra)",
    ram: "16GB LPDDR5x",
    storage: "1TB Gen4 NVMe SSD",
    display: "16\" 2.8K 2880×1800 OLED Touch 2-in-1",
    os: "Windows 11 Home",
    battery: "83Wh Li-ion",
    weight: "2.19 kg",
    condition: "New",
    sku: "LZ-009",
    description: "The HP Spectre x360 16 is HP's most premium consumer laptop — a stunning 2-in-1 convertible featuring an Intel Core Ultra 7 155H processor and a breathtaking 2.8K OLED touchscreen display.\n\nWith 16GB LPDDR5x RAM and a 1TB Gen4 NVMe SSD, this machine delivers flagship-tier performance for creative professionals, content creators, and power users. The OLED panel delivers vivid colours, deep blacks, and 100% DCI-P3 colour accuracy.\n\nBrand new and sealed in box — this is the pinnacle of laptop engineering in 2025.",
    tags: ["Spectre", "OLED", "2-in-1", "16 inch", "2K", "Ultra 7", "New", "Flagship"],
  },
  {
    id: 10,
    name: "HP ZBook Power 15 G8 | 15\" | i7 11th Gen 11850H | 16GB 512GB | 4GB NVIDIA Quadro T1200",
    price: 175000,
    oldPrice: 210000,
    badge: "Pre-Owned",
    badgeClass: "",
    specs: ["i7 11th Gen", "16GB RAM", "512GB SSD", "NVIDIA T1200"],
    img: "https://hf-store.pk/wp-content/uploads/2025/05/WhatsApp-Image-2025-05-03-at-5.05.54-PM-400x289.jpeg",
    rating: 4.7,
    hasOptions: false,
    processor: "Intel Core i7-11850H",
    processorGen: "11th Gen",
    ram: "16GB DDR4 ECC",
    storage: "512GB NVMe SSD",
    display: "15.6\" FHD 1080p IPS Anti-Glare",
    os: "Windows 11 Pro",
    battery: "83Wh Li-ion",
    weight: "2.03 kg",
    condition: "Pre-Owned",
    sku: "LZ-010",
    description: "The HP ZBook Power 15 G8 is a full-power mobile workstation built for engineers, architects, and 3D designers. The Intel Core i7-11850H 8-core processor combined with 4GB NVIDIA RTX A2000 (Quadro T1200) GPU handles CAD, 3D rendering, and simulation with ease.\n\n16GB DDR4 ECC RAM ensures reliability for mission-critical workloads, while the 512GB NVMe SSD keeps data loading fast. The ISV-certified GPU drivers ensure compatibility with professional software like AutoCAD, SolidWorks, and Adobe Creative Suite.\n\nA powerful pre-owned workstation at a fraction of the new price.",
    tags: ["ZBook", "Workstation", "15 inch", "i7", "NVIDIA", "Quadro", "GPU", "Pre-Owned"],
  },
  {
    id: 11,
    name: "HP ZBook 15 G5 | i7 8th Gen 8850H | 15\" 1080P | 4GB Nvidia Quadro P1000 | 16GB RAM 256GB SSD",
    price: 113000,
    oldPrice: 130000,
    badge: "Pre-Owned",
    badgeClass: "",
    specs: ["i7 8th Gen", "16GB RAM", "256GB SSD", "Quadro P1000"],
    img: "https://hf-store.pk/wp-content/uploads/2023/06/IMG_20230625_162724_288-e1770029283418-400x297.jpg",
    rating: 4.2,
    hasOptions: false,
    processor: "Intel Core i7-8850H",
    processorGen: "8th Gen",
    ram: "16GB DDR4 ECC",
    storage: "256GB NVMe SSD",
    display: "15.6\" FHD 1080p IPS DreamColor",
    os: "Windows 11 Pro",
    battery: "90Wh Li-ion",
    weight: "2.21 kg",
    condition: "Pre-Owned",
    sku: "LZ-011",
    description: "The HP ZBook 15 G5 is a proven 15.6\" mobile workstation powered by the Intel Core i7-8850H 6-core processor and backed by a professional-grade 4GB NVIDIA Quadro P1000 GPU.\n\nThis machine is designed for engineers, video editors, and architects who need certified GPU drivers and reliable performance. The HP DreamColor display delivers wide colour gamut reproduction perfect for colour-sensitive creative work. 16GB ECC RAM and 256GB NVMe SSD complete the package.\n\nPre-owned and fully tested — a workhorse workstation at a very accessible price.",
    tags: ["ZBook", "Workstation", "15 inch", "i7", "Quadro", "DreamColor", "Pre-Owned"],
  },
  {
    id: 12,
    name: "HP Elite x360 Dragonfly G2 | 13\" 1080p | i7 11th Gen 1185G7 | 32GB RAM 256GB SSD",
    price: 150000,
    oldPrice: 178000,
    badge: "Pre-Owned",
    badgeClass: "",
    specs: ["i7 11th Gen", "32GB RAM", "256GB SSD", "13\""],
    img: "https://hf-store.pk/wp-content/uploads/2024/10/WhatsApp-Image-2024-10-02-at-6.02.58-AM-400x300.jpeg",
    rating: 4.6,
    hasOptions: false,
    processor: "Intel Core i7-1185G7",
    processorGen: "11th Gen",
    ram: "32GB LPDDR4x",
    storage: "256GB NVMe SSD",
    display: "13.3\" FHD 1080p IPS Touch 2-in-1",
    os: "Windows 11 Pro",
    battery: "56Wh Li-ion",
    weight: "0.99 kg",
    condition: "Pre-Owned",
    sku: "LZ-012",
    description: "The HP Elite Dragonfly G2 is HP's most prestigious and ultra-portable 2-in-1 — weighing under 1 kg, it's the lightest business laptop in HP's entire portfolio. Despite its featherweight build, it houses a powerful Intel Core i7-1185G7 with Intel Iris Xe graphics.\n\nWith a massive 32GB LPDDR4x soldered RAM, this machine handles heavy multitasking, virtual machines, and data-heavy applications without hesitation. The 13.3\" FHD touchscreen with 360° hinge makes it a joy to use in any scenario.\n\nAn extraordinary pre-owned find — the Dragonfly rarely appears at this price point.",
    tags: ["Dragonfly", "2-in-1", "13 inch", "i7", "Ultra-portable", "Touch", "Pre-Owned"],
  },
  {
    id: 13,
    name: "HP EliteBook 850 G7 | i5 10th Gen 10610U CPU | 15 inch 1080p Display | 16GB Ram 256GB SSD | Pre-Owned Laptop",
    price: 97000,
    oldPrice: 115000,
    badge: "Pre-Owned",
    badgeClass: "",
    specs: ["i5 10th Gen", "16GB RAM", "256GB SSD", "15\""],
    img: "https://hf-store.pk/wp-content/uploads/2024/02/WhatsApp-Image-2025-05-02-at-10.34.54-PM-400x295.jpeg",
    rating: 4.4,
    hasOptions: false,
    processor: "Intel Core i5-10610U",
    processorGen: "10th Gen",
    ram: "16GB DDR4",
    storage: "256GB NVMe SSD",
    display: "15.6\" FHD 1080p IPS Anti-Glare",
    os: "Windows 11 Pro",
    battery: "56Wh Li-ion",
    weight: "1.78 kg",
    condition: "Pre-Owned",
    sku: "LZ-013",
    description: "The HP EliteBook 850 G7 brings EliteBook-grade build quality and security to a larger 15.6\" screen. The Intel Core i5-10610U vPro processor delivers reliable performance for enterprise workloads while keeping power consumption low.\n\n16GB DDR4 RAM and a 256GB NVMe SSD provide a snappy everyday experience. The anti-glare FHD IPS screen is comfortable for extended work sessions in varied lighting conditions.\n\nA solid, well-built business laptop available at a fraction of its original cost.",
    tags: ["EliteBook", "15 inch", "i5", "10th Gen", "vPro", "Pre-Owned"],
  },
  {
    id: 14,
    name: "HP EliteBook X360 1040 G8 | 14 inch 1080p Display | i7 11th Gen 1185G7 CPU | 32GB Ram 512GB SSD | Pre-Owned Laptop",
    price: 143000,
    oldPrice: 168000,
    badge: "Pre-Owned",
    badgeClass: "",
    specs: ["i7 11th Gen", "32GB RAM", "512GB SSD", "14\""],
    img: "https://hf-store.pk/wp-content/uploads/2024/02/image00001-1-2-scaled-e1713359837545-400x300.jpeg",
    rating: 4.7,
    hasOptions: false,
    processor: "Intel Core i7-1185G7",
    processorGen: "11th Gen",
    ram: "32GB LPDDR4x",
    storage: "512GB NVMe SSD",
    display: "14\" FHD 1080p IPS Touch 2-in-1",
    os: "Windows 11 Pro",
    battery: "51Wh Li-ion",
    weight: "1.36 kg",
    condition: "Pre-Owned",
    sku: "LZ-014",
    description: "The HP EliteBook X360 1040 G8 is a class-leading 14\" business 2-in-1 convertible. With the Intel Core i7-1185G7 — one of Intel's fastest 11th Gen mobile chips — it handles everything from spreadsheets to video editing and light 3D work.\n\n32GB LPDDR4x RAM ensures you can keep dozens of tabs, virtual machines, and productivity apps open simultaneously. The 512GB NVMe SSD provides both capacity and blazing speed. The 14\" FHD IPS touchscreen with 360° hinge makes it a true all-rounder.\n\nAn outstanding pre-owned premium 2-in-1 at a very competitive price.",
    tags: ["EliteBook", "2-in-1", "14 inch", "i7", "Touch", "11th Gen", "Pre-Owned"],
  },
  {
    id: 15,
    name: "HP EliteBook 850 G7 | i7 10th Gen 10610U CPU | 15 inch 1080p Display | 16GB Ram 256GB SSD | Pre-Owned Laptop",
    price: 105000,
    oldPrice: 125000,
    badge: "Pre-Owned",
    badgeClass: "",
    specs: ["i7 10th Gen", "16GB RAM", "256GB SSD", "15\""],
    img: "https://hf-store.pk/wp-content/uploads/2024/02/WhatsApp-Image-2025-05-02-at-10.34.54-PM-400x295.jpeg",
    rating: 4.5,
    hasOptions: false,
    processor: "Intel Core i7-10610U",
    processorGen: "10th Gen",
    ram: "16GB DDR4",
    storage: "256GB NVMe SSD",
    display: "15.6\" FHD 1080p IPS Anti-Glare",
    os: "Windows 11 Pro",
    battery: "56Wh Li-ion",
    weight: "1.78 kg",
    condition: "Pre-Owned",
    sku: "LZ-015",
    description: "The HP EliteBook 850 G7 with the i7-10610U is the performance-tier variant of the 850 series. The vPro-enabled Core i7 processor with 4.9 GHz boost speed handles demanding tasks, data analysis, and multitasking with impressive speed.\n\n16GB DDR4 RAM and a 256GB NVMe SSD ensure a smooth, responsive experience. HP's Sure Start, Sure Run, and HP Wolf Security features keep this laptop secure for enterprise environments.\n\nA premium pre-owned business laptop offering serious performance at a fraction of its original price.",
    tags: ["EliteBook", "15 inch", "i7", "10th Gen", "vPro", "Pre-Owned"],
  },
  {
    id: 16,
    name: "HP EliteBook 840 G7 | i5 10th Gen 10310U CPU | 14 inch 1080p Display | 8GB Ram 256GB SSD | Pre-Owned Laptop",
    price: 77000,
    oldPrice: 92000,
    badge: "Pre-Owned",
    badgeClass: "",
    specs: ["i5 10th Gen", "8GB RAM", "256GB SSD", "14\""],
    img: "https://hf-store.pk/wp-content/uploads/2023/07/WhatsApp-Image-2024-12-14-at-05.01.51_adf86389-e1734181491750-394x300.jpg",
    rating: 4.3,
    hasOptions: false,
    processor: "Intel Core i5-10310U",
    processorGen: "10th Gen",
    ram: "8GB DDR4",
    storage: "256GB NVMe SSD",
    display: "14\" FHD 1080p IPS Anti-Glare",
    os: "Windows 11 Pro",
    battery: "53Wh Li-ion",
    weight: "1.46 kg",
    condition: "Pre-Owned",
    sku: "LZ-016",
    description: "The HP EliteBook 840 G7 is the classic 14\" business ultrabook — slim, robust, and powerful enough for professional workloads. The Intel Core i5-10310U with vPro technology ensures reliable performance and enterprise-grade security.\n\nAt 1.46 kg and 14 inches, it strikes the ideal balance between portability and screen real estate. 8GB DDR4 RAM and a 256GB NVMe SSD keep everyday tasks fast and fluid.\n\nAn excellent entry into the EliteBook 840 line — pre-owned, fully tested, and great value for money.",
    tags: ["EliteBook", "14 inch", "i5", "10th Gen", "Ultrabook", "Pre-Owned"],
  },
];



// ─── STAR RATING HELPER ───
function starsHTML(rating) {
  const full = Math.floor(rating);
  const half = (rating % 1) >= 0.5 ? 1 : 0;
  const empty = 5 - full - half;
  return '<span class="stars">'
    + '<i class="fas fa-star"></i>'.repeat(full)
    + (half ? '<i class="fas fa-star-half-stroke"></i>' : '')
    + '<i class="far fa-star"></i>'.repeat(empty)
    + ` <span class="rating-num">${rating}</span>`
    + '</span>';
}

// ─── STATE ───
let cartCount = 0;
let currentData = [...laptops];
let currentView = "grid";
let maxPrice = 350000;

// ─── RENDER PRODUCTS ───
function renderProducts(data) {
  const grid = document.getElementById("productGrid");
  if (!data.length) {
    grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:60px;color:#888;">
      <i class="fa fa-laptop" style="font-size:3rem;opacity:0.3;display:block;margin-bottom:12px;"></i>
      No products match your filters.
    </div>`;
    return;
  }

  grid.innerHTML = data.map(p => {
    const priceDisplay = p.priceRange
      ? p.priceRange
      : "₨" + p.price.toLocaleString("en-PK");
    const oldPriceHTML = p.oldPrice
      ? `<span class="old-price">₨${p.oldPrice.toLocaleString("en-PK")}</span>`
      : "";
    const actionBtn = p.hasOptions
      ? `<button class="btn-options" onclick="event.stopPropagation()">Select Options</button>`
      : `<button class="btn-cart" onclick="addToCart(event, ${p.id})">
           <i class="fa fa-cart-plus"></i> Add to Cart
         </button>`;

    return `
      <div class="product-card" onclick="viewProduct(${p.id})">
        <div class="product-img-wrap">
          <img src="${p.img}" alt="${p.name}" loading="lazy" />
        </div>
        <div class="product-body">
          <p class="product-name">${p.name}</p>
          <div class="product-specs">
            ${p.specs.map(s => `<span class="spec-tag">${s}</span>`).join("")}
          </div>
          <div class="product-rating">${starsHTML(p.rating)}</div>
          <div class="product-price">${priceDisplay}${oldPriceHTML}</div>
          ${actionBtn}
        </div>
      </div>`;
  }).join("");
}

// ─── ADD TO CART ───
function addToCart(e, id) {
  e.stopPropagation();
  cartCount++;
  document.getElementById("cartCount").textContent = cartCount;
  showToast();
}

function showToast() {
  const toast = document.getElementById("toast");
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2500);
}

// ─── VIEW PRODUCT ───
function viewProduct(id) {
  const p = laptops.find(l => l.id === id);
  if (!p) return;

  // Breadcrumb
  document.getElementById("pd-crumb-name").textContent = p.name.split(" | ")[0].trim();

  // Image
  const img = document.getElementById("pd-main-img");
  img.src = p.img;
  img.alt = p.name;

  // Badge & SKU
  const badgeEl = document.getElementById("pd-badge");
  badgeEl.textContent = p.badge || "Pre-Owned";
  badgeEl.className = "pd-badge" + (p.badgeClass === "new" ? " new" : "");
  document.getElementById("pd-sku").textContent = p.sku ? "SKU: " + p.sku : "";

  // Name & rating
  document.getElementById("pd-name").textContent = p.name;
  document.getElementById("pd-rating").innerHTML =
    starsHTML(p.rating) + ` <span style="color:#888;font-size:0.8rem;">(${Math.round(p.rating * 12)} reviews)</span>`;

  // Price
  const priceDisplay = p.priceRange || ("₨" + p.price.toLocaleString("en-PK"));
  document.getElementById("pd-price").textContent = priceDisplay;
  const oldEl = document.getElementById("pd-old-price");
  const saveEl = document.getElementById("pd-saving");
  if (p.oldPrice) {
    oldEl.textContent = "₨" + p.oldPrice.toLocaleString("en-PK");
    oldEl.style.display = "";
    const pct = Math.round((1 - p.price / p.oldPrice) * 100);
    saveEl.textContent = pct + "% OFF";
    saveEl.style.display = "";
  } else {
    oldEl.style.display = "none";
    saveEl.style.display = "none";
  }

  // Quick spec chips
  const chips = [
    { icon: "fa-microchip", label: "Processor", val: p.processor },
    { icon: "fa-memory",    label: "RAM",       val: p.ram },
    { icon: "fa-hdd",       label: "Storage",   val: p.storage },
    { icon: "fa-desktop",   label: "Display",   val: p.display },
  ];
  document.getElementById("pd-specs-quick").innerHTML = chips
    .filter(c => c.val)
    .map(c => `
      <div class="pd-spec-chip">
        <i class="fa ${c.icon}"></i>
        <div><strong>${c.label}</strong><span>${c.val}</span></div>
      </div>`).join("");

  // Cart button
  document.getElementById("pd-cart-btn").onclick = function () {
    cartCount++;
    document.getElementById("cartCount").textContent = cartCount;
    showToast();
  };

  // WhatsApp
  const waText = encodeURIComponent("I'm interested in: " + p.name + " — Price: " + priceDisplay);
  document.getElementById("pd-wa-btn").href = "https://wa.me/923060024442?text=" + waText;

  // Tags
  document.getElementById("pd-tags").innerHTML = (p.tags || p.specs || [])
    .map(t => `<span class="pd-tag">${t}</span>`).join("");

  // Description tab
  const descLines = (p.description || p.name + " — a fully tested, pre-owned laptop in excellent condition.").split("\n").filter(Boolean);
  document.getElementById("tab-description").innerHTML =
    `<div class="pd-description">${descLines.map(l => `<p>${l}</p>`).join("")}</div>`;

  // Specs tab
  const rows = [
    ["Processor",        p.processor],
    ["Generation",       p.processorGen],
    ["RAM",              p.ram],
    ["Storage",          p.storage],
    ["Display",          p.display],
    ["Operating System", p.os],
    ["Battery",          p.battery],
    ["Weight",           p.weight],
    ["Condition",        p.condition || p.badge],
    ["SKU",              p.sku],
  ].filter(r => r[1]);
  document.getElementById("tab-specs").innerHTML =
    `<table class="pd-spec-table">${rows.map(r => `<tr><td>${r[0]}</td><td>${r[1]}</td></tr>`).join("")}</table>`;

  // Related products (4 random, exclude current)
  const related = laptops.filter(l => l.id !== id).sort(() => Math.random() - 0.5).slice(0, 4);
  document.getElementById("pd-related-grid").innerHTML = related.map(l => {
    const rPrice = l.priceRange || ("₨" + l.price.toLocaleString("en-PK"));
    return `
      <div class="product-card" onclick="viewProduct(${l.id})" style="cursor:pointer;">
        <div class="product-img-wrap">
          <img src="${l.img}" alt="${l.name}" loading="lazy" />
        </div>
        <div class="product-body">
          <p class="product-name">${l.name}</p>
          <div class="product-specs">${l.specs.map(s => `<span class="spec-tag">${s}</span>`).join("")}</div>
          <div class="product-price">${rPrice}</div>
        </div>
      </div>`;
  }).join("");

  // Reset tabs & show product page
  switchTab("description");
  document.querySelector("main.main-layout").style.display = "none";
  document.querySelector(".category-banner").style.display = "none";
  document.getElementById("product-page").style.display = "block";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ─── BACK TO LISTING ───
function showListing() {
  document.getElementById("product-page").style.display = "none";
  document.querySelector("main.main-layout").style.display = "";
  document.querySelector(".category-banner").style.display = "";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ─── TAB SWITCHER ───
function switchTab(tab) {
  document.querySelectorAll(".pd-tab-btn").forEach((btn, i) => {
    btn.classList.toggle("active", (i === 0 && tab === "description") || (i === 1 && tab === "specs"));
  });
  document.getElementById("tab-description").classList.toggle("active", tab === "description");
  document.getElementById("tab-specs").classList.toggle("active", tab === "specs");
}

// ─── SORT ───
function sortProducts() {
  const val = document.getElementById("sortSelect").value;
  let sorted = [...currentData];
  if (val === "price-asc") sorted.sort((a, b) => a.price - b.price);
  else if (val === "price-desc") sorted.sort((a, b) => b.price - a.price);
  else if (val === "name") sorted.sort((a, b) => a.name.localeCompare(b.name));
  else sorted = [...laptops].filter(p => p.price <= maxPrice);
  renderProducts(sorted);
}

// ─── PRICE FILTER ───
function updatePrice(val) {
  maxPrice = parseInt(val);
  document.getElementById("priceVal").textContent = "₨" + parseInt(val).toLocaleString("en-PK");
}
function filterPrice() {
  currentData = laptops.filter(p => p.price <= maxPrice);
  renderProducts(currentData);
}

// ─── VIEW TOGGLE ───
function setView(type) {
  currentView = type;
  const grid = document.getElementById("productGrid");
  const btns = document.querySelectorAll(".view-btn");
  btns.forEach(b => b.classList.remove("active"));
  if (type === "grid") {
    grid.classList.remove("list-view");
    btns[0].classList.add("active");
  } else {
    grid.classList.add("list-view");
    btns[1].classList.add("active");
  }
}

// ─── INIT ───
renderProducts(laptops);

// Deep-link support: ?product_id=N opens that product directly
// (used when the chat widget redirects a visitor to a specific product page)
(function () {
  var params = new URLSearchParams(window.location.search);
  var pid = parseInt(params.get("product_id"), 10);
  if (pid && !isNaN(pid)) {
    // Defer until the DOM has settled so all elements exist
    setTimeout(function () { viewProduct(pid); }, 0);
  }
})();
