const { createApp, ref, reactive, computed, onMounted, watch, nextTick } = Vue

createApp({
  setup() {
    const page = ref('items')
    const theme = ref(localStorage.getItem('theme') || 'light')
    const mobile = ref(window.innerWidth < 768)
    const sidebarCollapsed = ref(mobile.value)
    const items = ref([])
    const categories = ref([])
    const search = ref('')
    const filterCat = ref('')
    const filterStatus = ref('')
    const filtered = ref([])
    const alerts = ref([])
    const stats = ref({})
    const showForm = ref(false)
    const showCatForm = ref(false)
    const editingItem = ref(null)
    const detailItem = ref(null)
    const photoQuery = ref('')
    const photoResults = ref([])
    const formPhotoPreview = ref('')
    const formPhotoFile = ref(null)

    const form = reactive({
      name: '', category_id: null, purchase_date: '', price: 0,
      expected_lifespan_months: null, status: '在用', disposal_date: null,
      warranty_months: null, notes: ''
    })

    const catForm = reactive({ id: null, name: '', icon: '' })

    window.addEventListener('resize', () => {
      mobile.value = window.innerWidth < 768
      if (!mobile.value) sidebarCollapsed.value = false
      else sidebarCollapsed.value = true
    })

    function toggleTheme() {
      theme.value = theme.value === 'light' ? 'dark' : 'light'
      localStorage.setItem('theme', theme.value)
      document.documentElement.setAttribute('data-theme', theme.value)
    }
    onMounted(() => {
      document.documentElement.setAttribute('data-theme', theme.value)
    })

    const totalSpent = computed(() => {
      return items.value.reduce((s, i) => s + (i.price || 0), 0).toFixed(0)
    })

    async function api(url, opts = {}) {
      if (opts.body && typeof opts.body === 'object') {
        opts.body = JSON.stringify(opts.body)
      }
      const res = await fetch(url, {
        headers: { 'Content-Type': 'application/json' },
        ...opts,
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || res.statusText)
      }
      return res.json()
    }

    async function loadItems() {
      const data = await api('/api/items')
      items.value = data
      filterItems()
      const s = await api('/api/stats')
      alerts.value = s.warranty_alerts || []
    }

    async function loadCategories() {
      categories.value = await api('/api/categories')
    }

    function filterItems() {
      let list = [...items.value]
      if (search.value) {
        const q = search.value.toLowerCase()
        list = list.filter(i => i.name && i.name.toLowerCase().includes(q))
      }
      if (filterCat.value) {
        list = list.filter(i => i.category_id == filterCat.value)
      }
      if (filterStatus.value) {
        list = list.filter(i => i.status === filterStatus.value)
      }
      filtered.value = list
    }

    async function loadStats() {
      stats.value = await api('/api/stats')
      await nextTick()
      renderCharts()
    }

    let charts = []
    function renderCharts() {
      charts.forEach(c => c.destroy())
      charts = []
      const s = stats.value
      if (!s || !s.cat_pie) return

      const colors = ['#6366f1','#10b981','#f59e0b','#ef4444','#8b5cf6','#ec4899','#06b6d4','#84cc16']

      const pie = document.getElementById('pieChart')
      if (pie) {
        const c = new Chart(pie, {
          type: 'doughnut',
          data: {
            labels: s.cat_pie.map(d => d.name),
            datasets: [{ data: s.cat_pie.map(d => d.value), backgroundColor: colors, borderWidth: 0 }]
          },
          options: {
            plugins: { legend: { position: 'bottom', labels: { padding: 16, usePointStyle: true, pointStyleWidth: 8, font: { size: 12 } } } }
          }
        })
        charts.push(c)
      }

      const m = document.getElementById('monthChart')
      if (m && s.monthly_trend?.length > 0) {
        const c = new Chart(m, {
          type: 'line',
          data: {
            labels: s.monthly_trend.map(d => d.month),
            datasets: [{ label: '花费', data: s.monthly_trend.map(d => d.value), borderColor: '#6366f1', backgroundColor: 'rgba(99,102,241,0.08)', fill: true, tension: 0.3, pointRadius: 3 }]
          },
          options: {
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.04)' } }, x: { grid: { display: false } } }
          }
        })
        charts.push(c)
      }

      const y = document.getElementById('yearChart')
      if (y && s.yearly_trend?.length > 0) {
        const c = new Chart(y, {
          type: 'bar',
          data: {
            labels: s.yearly_trend.map(d => d.year),
            datasets: [{ label: '年度花费', data: s.yearly_trend.map(d => d.value), backgroundColor: '#818cf8', borderRadius: 6 }]
          },
          options: {
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.04)' } }, x: { grid: { display: false } } }
          }
        })
        charts.push(c)
      }

      const co = document.getElementById('costChart')
      if (co && s.top_cost_per_day?.length > 0) {
        const c = new Chart(co, {
          type: 'bar',
          data: {
            labels: s.top_cost_per_day.map(d => d.name),
            datasets: [{ label: '日均(元)', data: s.top_cost_per_day.map(d => d.cost_per_day), backgroundColor: '#f59e0b', borderRadius: 6 }]
          },
          options: {
            indexAxis: 'y',
            plugins: { legend: { display: false } },
            scales: { x: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.04)' } }, y: { grid: { display: false } } }
          }
        })
        charts.push(c)
      }
    }

    function openAdd() {
      Object.assign(form, {
        name: '', category_id: null, purchase_date: new Date().toISOString().slice(0,10),
        price: 0, expected_lifespan_months: null, status: '在用',
        disposal_date: null, warranty_months: null, notes: ''
      })
      editingItem.value = null
      formPhotoPreview.value = ''
      formPhotoFile.value = null
      photoResults.value = []
      photoQuery.value = ''
      showForm.value = true
    }

    function openEdit(item) {
      Object.assign(form, {
        name: item.name, category_id: item.category_id,
        purchase_date: item.purchase_date, price: item.price,
        expected_lifespan_months: item.expected_lifespan_months,
        status: item.status, disposal_date: item.disposal_date || null,
        warranty_months: item.warranty_months, notes: item.notes || ''
      })
      editingItem.value = item
      formPhotoPreview.value = ''
      formPhotoFile.value = null
      photoResults.value = []
      photoQuery.value = ''
      showForm.value = true
      detailItem.value = null
    }

    async function saveItem() {
      const payload = { ...form }
      if (!payload.category_id) payload.category_id = null
      if (!payload.expected_lifespan_months) payload.expected_lifespan_months = null
      if (!payload.warranty_months) payload.warranty_months = null
      if (payload.status === '在用') payload.disposal_date = null

      try {
        let itemId
        if (editingItem.value) {
          await api(`/api/items/${editingItem.value.id}`, { method: 'PUT', body: payload })
          itemId = editingItem.value.id
        } else {
          const r = await api('/api/items', { method: 'POST', body: payload })
          itemId = r.id
        }
        if (formPhotoFile.value) {
          const fd = new FormData()
          fd.append('file', formPhotoFile.value)
          await fetch(`/api/items/${itemId}/photo`, { method: 'POST', body: fd })
        }
        showForm.value = false
        await loadItems()
      } catch (e) {
        alert('保存失败: ' + e.message)
      }
    }

    async function deleteItem(id) {
      if (!confirm('确定删除？')) return
      await api(`/api/items/${id}`, { method: 'DELETE' })
      detailItem.value = null
      await loadItems()
    }

    function openDetail(item) {
      detailItem.value = items.value.find(i => i.id === item.id) || item
    }

    function onPhotoFile(e) {
      const file = e.target.files[0]
      if (!file) return
      formPhotoFile.value = file
      const reader = new FileReader()
      reader.onload = ev => { formPhotoPreview.value = ev.target.result }
      reader.readAsDataURL(file)
    }

    async function searchPhoto() {
      if (!photoQuery.value) return
      try {
        const data = await api(`/api/images/search?q=${encodeURIComponent(photoQuery.value)}`)
        photoResults.value = data
      } catch (e) {
        alert('搜图失败: ' + e.message)
      }
    }

    function pickPhoto(url) {
      formPhotoPreview.value = url
      fetch(url).then(r => r.blob()).then(blob => {
        formPhotoFile.value = new File([blob], 'photo.jpg', { type: blob.type })
      }).catch(() => {})
    }

    function catName(id) {
      const c = categories.value.find(x => x.id === id)
      return c ? c.name : '未分类'
    }
    function catIcon(id) {
      const c = categories.value.find(x => x.id === id)
      return c ? c.icon : '📦'
    }
    function editCat(c) {
      Object.assign(catForm, { id: c.id, name: c.name, icon: c.icon })
      showCatForm.value = true
    }
    async function saveCat() {
      if (catForm.id) {
        await api(`/api/categories/${catForm.id}`, { method: 'PUT', body: { name: catForm.name, icon: catForm.icon } })
      } else {
        await api('/api/categories', { method: 'POST', body: { name: catForm.name, icon: catForm.icon } })
      }
      showCatForm.value = false
      await loadCategories()
    }
    async function deleteCat(id) {
      if (!confirm('删除后该分类物品将变为未分类，确定？')) return
      await api(`/api/categories/${id}`, { method: 'DELETE' })
      await loadCategories()
      await loadItems()
    }

    function exportJSON() { window.open('/api/export/json') }
    function exportCSV() { window.open('/api/export/csv') }
    async function doBackup() {
      const r = await api('/api/backup', { method: 'POST' })
      alert('备份完成')
    }

    onMounted(() => {
      const el = document.getElementById('vue-status')
      if (el) el.remove()
      loadItems()
      loadCategories()
    })

    return {
      page, theme, mobile, sidebarCollapsed,
      items, categories, search, filterCat, filterStatus, filtered,
      alerts, stats,
      showForm, showCatForm, editingItem, detailItem,
      form, catForm, photoQuery, photoResults, formPhotoPreview,
      totalSpent,
      toggleTheme, filterItems, loadStats,
      openAdd, openEdit, saveItem, deleteItem, openDetail,
      onPhotoFile, searchPhoto, pickPhoto,
      catName, catIcon, editCat, saveCat, deleteCat,
      exportJSON, exportCSV, doBackup,
    }
  }
}).mount('#app')
