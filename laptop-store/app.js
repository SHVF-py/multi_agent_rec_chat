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
    img: "https://upload.wikimedia.org/wikipedia/commons/9/9a/HP_EliteBook_840_G8.png",
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
    img: "https://upload.wikimedia.org/wikipedia/commons/d/db/HP_EliteBook_850_G5.png",
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
    img: "https://upload.wikimedia.org/wikipedia/commons/d/d7/HP_EliteBook_840_G4.png",
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
    img: "https://upload.wikimedia.org/wikipedia/commons/c/c5/HP_Elitebook_840_G1.png",
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
    img: "https://upload.wikimedia.org/wikipedia/commons/4/48/HP_EliteBook_x360_1020_G2.png",
    rating: 4.4,
    hasOptions: false,
  },
  {
    id: 6,
    name: "ZBook Firefly 14 G8 | 14\" 1080p | i5 11th Gen 1145G7 | 16GB RAM 256GB SSD",
    price: 93000,
    priceRange: "₨93,000 – ₨99,000",
    oldPrice: null,
    badge: "Pre-Owned",
    badgeClass: "",
    specs: ["i5 11th Gen", "16GB RAM", "256GB SSD", "14\""],
    img: "https://upload.wikimedia.org/wikipedia/commons/9/9a/HP_EliteBook_840_G8.png",
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
    img: "https://upload.wikimedia.org/wikipedia/commons/d/db/HP_EliteBook_850_G5.png",
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
    img: "https://upload.wikimedia.org/wikipedia/commons/d/d7/HP_EliteBook_840_G4.png",
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
    img: "https://upload.wikimedia.org/wikipedia/commons/1/1b/HP_Spectre_x360_2016_%2832003550180%29.jpg",
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
    img: "https://upload.wikimedia.org/wikipedia/commons/9/96/HP_Elitebook_8770w.png",
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
    img: "https://upload.wikimedia.org/wikipedia/commons/6/61/HP_EliteBook_8760w_%281%29.jpg",
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
    img: "https://upload.wikimedia.org/wikipedia/commons/5/5a/HP_Spectre_x360_2016_%2831538364704%29.jpg",
    rating: 4.6,
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
          <span class="badge ${p.badgeClass}">${p.badge}</span>
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
