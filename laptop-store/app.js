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
  if (p) alert(`Product: ${p.name}\nPrice: ₨${p.price.toLocaleString("en-PK")}\n\n(In a real store, this would open the product detail page.)`);
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
