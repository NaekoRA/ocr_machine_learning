<template>
  <div class="container">
    <h1>Manajemen keyword</h1>

    <div class="add-button-container">
      <button @click="openAddModal" class="add-new-keyword-button">
        + Tambah keyword Baru
      </button>
    </div>

    <div class="table-section">
      <h2>Daftar keyword</h2>

      <div class="search-wrapper">
        <input
          type="text"
          v-model="searchQuery"
          placeholder="Cari ID / keyword / normalized value..."
          class="search-input"
        />
      </div>

      <table id="keywordTable">
        <thead>
          <tr>
            <th @click="toggleSort('id')" style="cursor: pointer;">
              ID
              <span v-if="sortKey === 'id'">({{ sortOrder === 'asc' ? '↑' : '↓' }})</span>
            </th>
            <th @click="toggleSort('keyword')" style="cursor: pointer;">
              keywords
              <span v-if="sortKey === 'keyword'">({{ sortOrder === 'asc' ? '↑' : '↓' }})</span>
            </th>
            <th @click="toggleSort('normalized_value')" style="cursor: pointer;">
              normalized_value
              <span v-if="sortKey === 'normalized_value'">({{ sortOrder === 'asc' ? '↑' : '↓' }})</span>
            </th>
            <th>actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="filteredSortedKeywords.length === 0">
            <td colspan="4" style="text-align: center;">Tidak ada keyword ditemukan.</td>
          </tr>
          <tr v-for="kw in filteredSortedKeywords" :key="kw.id">
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

    <!-- Modal Tambah/Edit -->
    <div v-if="showModal" class="modal-overlay">
      <div class="modal-content">
        <h2>{{ editingKeyword ? 'Edit keyword' : 'Tambah keyword Baru' }}</h2>
        <form @submit.prevent="handleSubmit">
          <input type="hidden" v-model="form.id">

          <label for="keyword">keyword:</label>
          <input type="text" id="keyword" v-model="form.keyword" required>

          <label for="normalizedValue">normalized value:</label>
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
            <button type="submit">{{ editingKeyword ? 'Update keyword' : 'Tambah keyword' }}</button>
            <button type="button" @click="closeModal" class="cancel-button">Batal</button>
          </div>
        </form>
        <p v-if="formMessage" :class="['message', formMessageType]">{{ formMessage }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';

const API_BASE_URL = 'http://127.0.0.1:8000';

const keywords = ref([]);
const form = ref({ id: null, keyword: '', normalized_value: '' });
const editingKeyword = ref(false);
const showModal = ref(false);
const formMessage = ref('');
const formMessageType = ref('');
const tableMessage = ref('');
const tableMessageType = ref('');

const allDescriptionSuggestions = ref([]);
const filteredSuggestions = ref([]);
const activeSuggestionIndex = ref(-1);

const sortKey = ref('id');
const sortOrder = ref('asc');

const searchQuery = ref('');

const sortedKeywords = computed(() => {
  const sorted = [...keywords.value];
  sorted.sort((a, b) => {
    const aVal = a[sortKey.value];
    const bVal = b[sortKey.value];
    if (typeof aVal === 'string') {
      return sortOrder.value === 'asc'
        ? aVal.localeCompare(bVal)
        : bVal.localeCompare(aVal);
    }
    return sortOrder.value === 'asc' ? aVal - bVal : bVal - aVal;
  });
  return sorted;
});

// Filter setelah sortir
const filteredSortedKeywords = computed(() => {
  const query = searchQuery.value.toLowerCase();
  return sortedKeywords.value.filter(kw =>
    kw.id.toString().includes(query) ||
    kw.keyword.toLowerCase().includes(query) ||
    kw.normalized_value.toLowerCase().includes(query)
  );
});


function toggleSort(key) {
  if (sortKey.value === key) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc';
  } else {
    sortKey.value = key;
    sortOrder.value = 'asc';
  }
}

function showMessage(refName, message, type) {
  if (refName === 'form') {
    formMessage.value = message;
    formMessageType.value = type;
    setTimeout(() => (formMessage.value = ''), 5000);
  } else {
    tableMessage.value = message;
    tableMessageType.value = type;
    setTimeout(() => (tableMessage.value = ''), 5000);
  }
}

async function fetchKeywords() {
  try {
    const res = await fetch(`${API_BASE_URL}/keywords`);
    keywords.value = await res.json();
  } catch (err) {
    showMessage('table', `Gagal memuat keyword: ${err.message}`, 'error');
  }
}

async function fetchDescriptionSuggestions() {
  try {
    const res = await fetch(`${API_BASE_URL}/suggestions/descriptions`);
    allDescriptionSuggestions.value = await res.json();
  } catch (err) {
    console.error(err);
  }
}

function filterDescriptionSuggestions() {
  const currentWord = form.value.normalized_value.trim().split(/\s+/).pop().toLowerCase();
  if (!currentWord) return (filteredSuggestions.value = []);
  filteredSuggestions.value = allDescriptionSuggestions.value
    .filter(val => val.toLowerCase().includes(currentWord))
    .sort((a, b) => a.toLowerCase().startsWith(currentWord) ? -1 : 1);
  activeSuggestionIndex.value = -1;
}

function selectSuggestion(s) {
  const words = form.value.normalized_value.trim().split(/\s+/);
  words[words.length - 1] = s;
  form.value.normalized_value = words.join(' ') + ' ';
  filteredSuggestions.value = [];
  activeSuggestionIndex.value = -1;
}

function navigateSuggestions(dir) {
  if (!filteredSuggestions.value.length) return;
  activeSuggestionIndex.value += dir;
  const total = filteredSuggestions.value.length;
  if (activeSuggestionIndex.value < 0) activeSuggestionIndex.value = total - 1;
  if (activeSuggestionIndex.value >= total) activeSuggestionIndex.value = 0;
}

function selectActiveSuggestion() {
  if (activeSuggestionIndex.value !== -1) {
    selectSuggestion(filteredSuggestions.value[activeSuggestionIndex.value]);
  } else if (filteredSuggestions.value.length > 0) {
    selectSuggestion(filteredSuggestions.value[0]);
  }
}

async function handleSubmit() {
  const url = form.value.id
    ? `${API_BASE_URL}/keyword/${form.value.id}`
    : `${API_BASE_URL}/keywords`;
  const method = form.value.id ? 'PUT' : 'POST';

  try {
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form.value),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || 'Gagal menyimpan');
    showMessage('form', 'Berhasil disimpan', 'success');
    closeModal();
    await fetchKeywords();
  } catch (err) {
    showMessage('form', `Gagal: ${err.message}`, 'error');
  }
}

function openAddModal() {
  resetForm();
  editingKeyword.value = false;
  showModal.value = true;
  filteredSuggestions.value = [];
}

function editKeyword(kw) {
  form.value = { ...kw };
  editingKeyword.value = true;
  showModal.value = true;
  filteredSuggestions.value = [];
}

function closeModal() {
  showModal.value = false;
  resetForm();
  filteredSuggestions.value = [];
}

function resetForm() {
  form.value = { id: null, keyword: '', normalized_value: '' };
  formMessage.value = '';
  formMessageType.value = '';
}

async function deleteKeyword(id) {
  if (!confirm('Yakin ingin hapus?')) return;
  try {
    const res = await fetch(`${API_BASE_URL}/keywords/${id}`, { method: 'DELETE' });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || 'Gagal menghapus');
    showMessage('table', 'Berhasil dihapus', 'success');
    await fetchKeywords();
  } catch (err) {
    showMessage('table', `Gagal: ${err.message}`, 'error');
  }
}

onMounted(() => {
  fetchKeywords();
  fetchDescriptionSuggestions();
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