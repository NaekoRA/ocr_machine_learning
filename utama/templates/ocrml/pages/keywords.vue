<template>
  <div class="container">
    <h1>Manajemen Kata Kunci</h1>

    <div class="add-button-container">
      <button @click="openAddModal" class="add-new-keyword-button">
        + Tambah keyword Baru
      </button>
    </div>

    <div class="table-section">
      <h2>Daftar Kata Kunci</h2>
      <table id="keywordTable">
        <thead>
          <tr>
            <th>ID</th>
            <th>keywords</th>
            <th>normalized_value</th>
            <th>actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="keywords.length === 0">
            <td colspan="4" style="text-align: center;">Tidak ada kata kunci ditemukan.</td>
          </tr>
          <tr v-for="kw in keywords" :key="kw.id">
            <td>{{ kw.id }}</td>
            <td>{{ kw.keyword }}</td>
            <td>{{ kw.normalized_value }}</td>
            <td class="actions">
              <button @click="editKeyword(kw)" class="edit-button">Edit</button>
              <button @click="deleteKeyword(kw.id)" class="delete-button">Hapus</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="tableMessage" :class="['message', tableMessageType]">{{ tableMessage }}</p>
    </div>

    <div v-if="showModal" class="modal-overlay">
      <div class="modal-content">
        <h2>{{ editingKeyword ? 'Edit keyword' : 'Tambah keyword Baru' }}</h2>
        <form @submit.prevent="handleSubmit">
          <input type="hidden" v-model="form.id">
          <label for="keyword">Kata Kunci:</label>
          <input type="text" id="keyword" v-model="form.keyword" required>

          <label for="normalizedValue">Nilai Normalisasi:</label>
          <div class="autocomplete-wrapper">
            <input
              type="text"
              id="normalizedValue"
              v-model="form.normalized_value"
              @input="filterDescriptionSuggestions"
              @keydown.up.prevent="navigateSuggestions(-1)"
              @keydown.down.prevent="navigateSuggestions(1)"
              @keydown.enter.prevent="selectActiveSuggestion"
              @keydown.esc="filteredSuggestions = []"
              required
            />
            <ul v-if="filteredSuggestions.length > 0 && form.normalized_value.length > 0" class="suggestions-list">
              <li
                v-for="(suggestion, index) in filteredSuggestions"
                :key="index"
                @click="selectSuggestion(suggestion)"
                :class="{ 'active': index === activeSuggestionIndex }"
              >
                {{ suggestion }}
              </li>
            </ul>
          </div>

          <div class="form-actions">
            <button type="submit">{{ editingKeyword ? 'Update Kata Kunci' : 'Tambah Kata Kunci' }}</button>
            <button type="button" @click="closeModal" class="cancel-button">Batal</button>
          </div>
        </form>
        <p v-if="formMessage" :class="['message', formMessageType]">{{ formMessage }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const API_BASE_URL = 'http://127.0.0.1:8000'; // Pastikan ini sesuai dengan URL FastAPI Anda

const keywords = ref([]);
const form = ref({
  id: null,
  keyword: '',
  normalized_value: '',
});
const editingKeyword = ref(false);
const showModal = ref(false);
const formMessage = ref('');
const formMessageType = ref('');
const tableMessage = ref('');
const tableMessageType = ref('');

// Refs untuk saran dari Description data_pusat
const allDescriptionSuggestions = ref([]); // Akan menyimpan semua deskripsi unik dari data_pusat
const filteredSuggestions = ref([]);
const activeSuggestionIndex = ref(-1); // Untuk navigasi keyboard

// Fungsi untuk menampilkan pesan
function showMessage(elementRef, message, type) {
  if (elementRef === 'form') {
    formMessage.value = message;
    formMessageType.value = type;
    setTimeout(() => {
      formMessage.value = '';
      formMessageType.value = '';
    }, 5000);
  } else if (elementRef === 'table') {
    tableMessage.value = message;
    tableMessageType.value = type;
    setTimeout(() => {
      tableMessage.value = '';
      tableMessageType.value = '';
    }, 5000);
  }
}

// Mengambil data kata kunci dari API (untuk tabel utama)
async function fetchKeywords() {
  try {
    const response = await fetch(`${API_BASE_URL}/keywords`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    keywords.value = await response.json();
    tableMessage.value = ''; // Hapus pesan jika berhasil dimuat
  } catch (error) {
    console.error('Error fetching keywords:', error);
    showMessage('table', `Gagal memuat kata kunci: ${error.message}`, 'error');
  }
}

// FUNGSI BARU: Mengambil saran deskripsi dari endpoint FastAPI
async function fetchDescriptionSuggestions() {
  try {
    const response = await fetch(`${API_BASE_URL}/suggestions/descriptions`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    allDescriptionSuggestions.value = await response.json();
  } catch (error) {
    console.error('Error fetching description suggestions:', error);
  }
}

// FUNGSI BARU: Memfilter saran berdasarkan input deskripsi (bukan normalized_value dari keywords)
function filterDescriptionSuggestions() {
  const input = form.value.normalized_value;
  const words = input.split(/\s+/); // pisah berdasarkan spasi
  const currentWord = words[words.length - 1].toLowerCase(); // ambil kata terakhir

  if (currentWord.length === 0) {
    filteredSuggestions.value = [];
    activeSuggestionIndex.value = -1;
    return;
  }

  filteredSuggestions.value = allDescriptionSuggestions.value.filter(val =>
    val.toLowerCase().includes(currentWord)
  ).sort((a, b) => {
    const aLower = a.toLowerCase();
    const bLower = b.toLowerCase();
    if (aLower.startsWith(currentWord) && !bLower.startsWith(currentWord)) return -1;
    if (!aLower.startsWith(currentWord) && bLower.startsWith(currentWord)) return 1;
    return a.localeCompare(b);
  });

  activeSuggestionIndex.value = -1;
}


// Fungsi untuk memilih saran dari daftar
function selectSuggestion(suggestion) {
  const words = form.value.normalized_value.trim().split(/\s+/);
  words[words.length - 1] = suggestion; // ganti kata terakhir
  form.value.normalized_value = words.join(' ') + ' '; // tambahkan spasi agar bisa lanjut ketik
  filteredSuggestions.value = [];
  activeSuggestionIndex.value = -1;
}


// Navigasi dengan keyboard (atas/bawah)
function navigateSuggestions(direction) {
  if (filteredSuggestions.value.length === 0) return;

  activeSuggestionIndex.value += direction;

  if (activeSuggestionIndex.value < 0) {
    activeSuggestionIndex.value = filteredSuggestions.value.length - 1;
  } else if (activeSuggestionIndex.value >= filteredSuggestions.value.length) {
    activeSuggestionIndex.value = 0;
  }

  // Opsional: Scroll ke item yang aktif (untuk daftar yang panjang)
  const activeElement = document.querySelector('.suggestions-list li.active');
  if (activeElement) {
    activeElement.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  }
}

// Memilih saran aktif (dengan Enter)
function selectActiveSuggestion() {
  if (activeSuggestionIndex.value !== -1 && filteredSuggestions.value.length > 0) {
    selectSuggestion(filteredSuggestions.value[activeSuggestionIndex.value]);
  } else if (filteredSuggestions.value.length > 0) {
    // Jika tidak ada yang aktif tapi ada saran, pilih yang pertama
    selectSuggestion(filteredSuggestions.value[0]);
  }
  // Jika Enter ditekan dan tidak ada saran atau tidak ada yang aktif, form akan mencoba submit secara normal.
}


// Menangani submit formulir (Tambah/Edit)
async function handleSubmit() {
  const url = form.value.id
    ? `${API_BASE_URL}/keyword/${form.value.id}`
    : `${API_BASE_URL}/keywords`;
  const method = form.value.id ? 'PUT' : 'POST';

  try {
    const response = await fetch(url, {
      method: method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        keyword: form.value.keyword,
        normalized_value: form.value.normalized_value,
      }),
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.detail || `HTTP error! status: ${response.status}`);
    }

    showMessage('form', result.message || 'Operasi berhasil!', 'success');
    closeModal(); // Tutup modal saat berhasil
    await fetchKeywords(); // Muat ulang daftar kata kunci
  } catch (error) {
    console.error('Error saving keyword:', error);
    showMessage('form', `Gagal menyimpan kata kunci: ${error.message}`, 'error');
  }
}

// Membuka modal untuk menambah kata kunci baru
function openAddModal() {
  resetForm(); // Pastikan form bersih untuk entri baru
  editingKeyword.value = false;
  showModal.value = true;
  filteredSuggestions.value = []; // Bersihkan saran
}

// Mengisi formulir dan membuka modal untuk edit
function editKeyword(kw) {
  form.value.id = kw.id;
  form.value.keyword = kw.keyword;
  form.value.normalized_value = kw.normalized_value;
  editingKeyword.value = true;
  showModal.value = true; // Tampilkan modal untuk edit
  filteredSuggestions.value = []; // Bersihkan saran
}

// Menutup modal dan mereset formulir
function closeModal() {
  showModal.value = false;
  resetForm();
  filteredSuggestions.value = []; // Bersihkan saran saat ditutup
}

// Mereset formulir
function resetForm() {
  form.value = {
    id: null,
    keyword: '',
    normalized_value: '',
  };
  editingKeyword.value = false;
  formMessage.value = '';
  formMessageType.value = '';
}

// Menghapus kata kunci
async function deleteKeyword(id) {
  if (!confirm('Apakah Anda yakin ingin menghapus kata kunci ini?')) {
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/keywords/${id}`, {
      method: 'DELETE',
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.detail || `HTTP error! status: ${response.status}`);
    }

    showMessage('table', result.message || 'Kata kunci berhasil dihapus!', 'success');
    await fetchKeywords(); // Muat ulang daftar
  } catch (error) {
    console.error('Error deleting keyword:', error);
    showMessage('table', `Gagal menghapus kata kunci: ${error.message}`, 'error');
  }
}

// Panggil fetchKeywords DAN fetchDescriptionSuggestions saat komponen dimuat
onMounted(() => {
  fetchKeywords();
  fetchDescriptionSuggestions(); // Panggil fungsi baru ini untuk mendapatkan saran
});
</script>

<style scoped>
/* Anda bisa menempatkan CSS yang sama dari style.css Anda di sini,
    atau membuat file CSS global dan mengimpornya di nuxt.config.ts */

body {
  margin: 0;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background-color: #f4f7f6;
  color: #333;
}

.container {
  max-width: 900px;
  margin: 20px auto;
  background-color: #fff;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  position: relative;
}

h1, h2 {
  color: #0056b3;
  text-align: center;
  margin-bottom: 20px;
}

.form-section, .table-section {
  margin-bottom: 30px;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 5px;
  background-color: #fafafa;
}

form {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

label {
  font-weight: bold;
  margin-bottom: 5px;
  color: #555;
}

input[type="text"] {
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 16px;
  width: 100%;
  box-sizing: border-box;
}

.form-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 15px;
}

button {
  padding: 10px 18px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 16px;
  transition: background-color 0.3s ease, transform 0.2s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

button:hover {
  transform: translateY(-1px);
}

button[type="submit"] {
  background-color: #28a745;
  color: white;
}

button[type="submit"]:hover {
  background-color: #218838;
}

.cancel-button {
  background-color: #6c757d;
  color: white;
}

.cancel-button:hover {
  background-color: #5a6268;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}

th, td {
  border: 1px solid #ddd;
  padding: 12px;
  text-align: left;
}

th {
  background-color: #007bff;
  color: white;
  font-weight: bold;
}

tr:nth-child(even) {
  background-color: #f2f2f2;
}

.actions button {
  margin-right: 5px;
  padding: 8px 12px;
  font-size: 14px;
  border-radius: 4px;
}

.actions .edit-button {
  background-color: #ffc107;
  color: #333;
}

.actions .edit-button:hover {
  background-color: #e0a800;
}

.actions .delete-button {
  background-color: #dc3545;
  color: white;
}

.actions .delete-button:hover {
  background-color: #c82333;
}

.message {
  margin-top: 10px;
  padding: 10px;
  border-radius: 4px;
  font-weight: bold;
  text-align: center;
}

.message.success {
  background-color: #d4edda;
  color: #155724;
  border-color: #c3e6cb;
}

.message.error {
  background-color: #f8d7da;
  color: #721c24;
  border-color: #f5c6cb;
}

/* --- Modal Styles --- */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background-color: #fff;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
  width: 90%;
  max-width: 500px;
  position: relative;
  animation: fadeInScale 0.3s ease-out;
}

.modal-content h2 {
  margin-top: 0;
  margin-bottom: 25px;
  color: #0056b3;
  text-align: center;
}

/* --- Floating Add Button Styles --- */
.add-button-container {
  position: sticky; /* or 'fixed' */
  top: 20px; /* Adjust as needed */
  width: 100%;
  display: flex;
  justify-content: center;
  z-index: 999; /* Ensure it's above other content but below modal */
  margin-bottom: 20px; /* Space between button and table */
}

.add-new-keyword-button {
  background-color: #007bff;
  color: white;
  padding: 12px 25px;
  font-size: 18px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 4px 8px rgba(0, 123, 255, 0.2);
}

.add-new-keyword-button:hover {
  background-color: #0056b3;
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 123, 255, 0.3);
}

/* --- Autocomplete Styles --- */
.autocomplete-wrapper {
  position: relative;
}

.suggestions-list {
  position: absolute;
  background-color: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  max-height: 200px;
  overflow-y: auto;
  width: 100%;
  z-index: 100; /* Pastikan ini di atas elemen lain */
  list-style-type: none;
  padding: 0;
  margin-top: 5px; /* Jarak antara input dan daftar */
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.suggestions-list li {
  padding: 10px;
  cursor: pointer;
}

.suggestions-list li:hover,
.suggestions-list li.active {
  background-color: #f0f0f0;
}

/* Animations */
@keyframes fadeInScale {
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
</style>