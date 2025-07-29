<template>
  <div class="app-container">
    <nav class="navbar">
      <NuxtLink to="/" class="nav-brand">Struk Scanner</NuxtLink>
      <div class="nav-links">
        <NuxtLink to="/" class="nav-item">Scan Struk</NuxtLink>
        <NuxtLink to="/konfirmasi" class="nav-item">Konfirmasi OCR</NuxtLink>
        <NuxtLink to="/keywords" class="nav-item">Manajemen Keyword</NuxtLink>
        <NuxtLink to="/confirmed" class="nav-item">sudah di konfirmasi</NuxtLink>
      </div>
    </nav>
    <main class="main-content">
      <NuxtPage />
    </main>
  </div>
</template>

<script setup>
// Script setup jika ada (tidak wajib untuk layout ini)
</script>

<style>
/* --- GLOBAL RESET DAN DASAR LAYOUT --- */
html, body {
  margin: 0;
  padding: 0;
  height: 100%; /* Memastikan tinggi HTML dan Body penuh */
  width: 100%;  /* Memastikan lebar HTML dan Body penuh */
  font-family: Arial, sans-serif;
  background-color: #f4f7f6;
  overflow-y: auto; /* Izinkan scrolling vertikal jika konten melebihi tinggi */
  box-sizing: border-box; /* Penting untuk konsistensi model box */
}

/* Container utama aplikasi yang mengisi seluruh viewport */
.app-container {
  display: flex;
  flex-direction: column; /* Susun item secara vertikal */
  min-height: 100vh; /* Minimal tinggi viewport */
  width: 100%; /* Memastikan app-container mengisi seluruh lebar */
  box-sizing: border-box;
}

/* --- NAVBAR STYLING --- */
.navbar {
  display: flex;
  position: fixed;
  justify-content: space-between;
  align-items: center;
  background-color: #2c3e50;
  padding: 15px 30px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  flex-shrink: 0; /* Agar navbar tidak menyusut */
  width: 100%; /* Memastikan navbar mengisi seluruh lebar */
  box-sizing: border-box;
  z-index: 999;
}

.nav-brand {
  color: #ecf0f1;
  font-size: 1.8em;
  font-weight: bold;
  text-decoration: none;
}

.nav-links {
  display: flex;
  gap: 25px;
}

.nav-item {
  color: #bdc3c7;
  text-decoration: none;
  font-size: 1.1em;
  padding: 8px 15px;
  border-radius: 5px;
  transition: background-color 0.3s ease, color 0.3s ease;
}

.nav-item:hover,
.nav-item.router-link-active {
  background-color: #3498db;
  color: white;
}

/* --- MAIN CONTENT STYLING --- */
.main-content {
  flex-grow: 1; /* Konten ini akan mengambil semua ruang vertikal yang tersedia */
  /* Remove max-width and margin: 0 auto from here to allow it to fill width */
  padding: 30px 20px; /* Padding di sekitar konten halaman */
  width: 100%; /* Pastikan main-content mengisi lebar parent-nya */
  box-sizing: border-box;
  /* Tambahkan display flex untuk menengahkan konten halaman di dalamnya */
  display: flex;
  justify-content: center; /* Tengah secara horizontal */
  align-items: flex-start; /* Sejajarkan ke atas secara vertikal */
}

/* --- PAGE CONTAINER STYLING (Untuk konten spesifik halaman) --- */
/* Ini adalah div yang ada di index.vue, konfirmasi.vue, keywords.vue */
.container, .page-container {
    width: 100%; /* Kontainer halaman mengisi lebar parent-nya (main-content) */
    max-width: 800px; /* Batasi lebar KONTEN halaman agar tidak terlalu lebar dan tetap terbaca */
    /* margin: 0 auto; akan membuat konten halaman di tengah dalam main-content */
    background-color: #ffffff;
    padding: 30px;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
    box-sizing: border-box;
}

/* --- FOOTER STYLING --- */
.app-footer {
  background-color: #34495e;
  color: #ecf0f1;
  text-align: center;
  padding: 15px;
  font-size: 0.9em;
  flex-shrink: 0; /* Agar footer tidak menyusut */
  margin-top: auto; /* Mendorong footer ke bawah jika konten tidak penuh */
  width: 100%; /* Memastikan footer mengisi seluruh lebar */
  box-sizing: border-box;
}
</style>