import { Fragment, useCallback, useEffect, useMemo, useState } from 'react'
import {
  Activity, AlertTriangle, ArrowDownRight, ArrowRight, ArrowUpRight, BarChart3,
  Blocks, CalendarDays, Check, CheckCircle2, ChevronRight, Clock3, Download,
  Gauge, LayoutDashboard,
  Map, Menu, Moon, Pause, Play, Plus, Radio, Search, Send, Settings2, Sun,
  Pencil, ShieldCheck, SlidersHorizontal, Sparkles, TrainFront, Wrench, X,
} from 'lucide-react'
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

const API = import.meta.env.VITE_API_URL || ''
const NAV = [
  { id: 'Overview', icon: LayoutDashboard },
  { id: 'Block planner', icon: CalendarDays },
  { id: 'Maintenance', icon: Wrench },
  { id: 'Corridors', icon: Map },
  { id: 'Coordination hub', icon: Blocks },
  { id: 'Analytics', icon: BarChart3 },
  { id: 'System health', icon: Settings2 },
]
const fallbackTasks = [
  { id: 'TMS-2841', asset: 'Rail fracture inspection', location: 'KM 142/6 · BPL–ET', department: 'Engineering', source: 'TMS', priority: 'Critical', due: 'Overdue 2 days', duration: 3, corridor: 'BPL–ET', status: 'Unscheduled', criticality: 96 },
  { id: 'SMMS-1092', asset: 'Signal relay replacement', location: 'Itarsi Jn · Panel B', department: 'S&T', source: 'SMMS', priority: 'High', due: 'Due today', duration: 2, corridor: 'BPL–ET', status: 'Unscheduled', criticality: 84 },
  { id: 'TDMS-0638', asset: 'OHE insulator renewal', location: 'KM 88/3 · BINA–BPL', department: 'Traction', source: 'TDMS', priority: 'High', due: 'Due in 1 day', duration: 3, corridor: 'BINA–BPL', status: 'Unscheduled', criticality: 79 },
  { id: 'TMS-2790', asset: 'Points & crossing lubrication', location: 'Bhopal Jn · Line 4', department: 'Engineering', source: 'TMS', priority: 'Medium', due: 'Due in 3 days', duration: 2, corridor: 'BPL–ET', status: 'Unscheduled', criticality: 62 },
  { id: 'SMMS-1065', asset: 'Track circuit calibration', location: 'KM 56/2 · BINA–BPL', department: 'S&T', source: 'SMMS', priority: 'Medium', due: 'Due in 5 days', duration: 2, corridor: 'BINA–BPL', status: 'Unscheduled', criticality: 54 },
  { id: 'TDMS-0612', asset: 'Cantilever assembly inspection', location: 'KM 176/1 · BPL–ET', department: 'Traction', source: 'TDMS', priority: 'Low', due: 'Due in 8 days', duration: 2, corridor: 'BPL–ET', status: 'Unscheduled', criticality: 38 },
]
const fallbackBlocks = [
  { id: 'BLK-2401', corridor: 'BPL–ET', section: 'Bhopal – Itarsi', date: 'Today, 01:15–04:15', window: '01:15 – 04:15', duration: 3, departments: ['Engineering', 'S&T'], tasks: 2, status: 'Confirmed', trains: 4, availability: 92 },
  { id: 'BLK-2402', corridor: 'BINA–BPL', section: 'Bina – Bhopal', date: 'Tomorrow, 00:30–03:30', window: '00:30 – 03:30', duration: 3, departments: ['Traction'], tasks: 1, status: 'Proposed', trains: 3, availability: 95 },
  { id: 'BLK-2403', corridor: 'BPL–ET', section: 'Bhopal – Itarsi', date: 'Wed, 02:00–04:00', window: '02:00 – 04:00', duration: 2, departments: ['Engineering'], tasks: 1, status: 'Proposed', trains: 5, availability: 91 },
]
const fallbackHistory = Array.from({ length: 7 }, (_, index) => ({
  day: new Date(Date.now() - (6 - index) * 2000).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }),
  availability: Math.round((96.4 + (Math.random() - 0.5) * 0.5) * 10) / 10,
  blocks: 11 + Math.round((Math.random() - 0.5) * 3),
}))
const fallbackSimulation = {
  running: true,
  speed: 1,
  sampled_at: new Date().toISOString(),
  network_availability: 96.4,
  critical_asset_availability: 98.2,
  blocks_scheduled: 11,
  tasks_coordinated: 24,
  changes: { network_availability: 0, critical_asset_availability: 0, blocks_scheduled: 0, tasks_coordinated: 0 },
  corridors: [
    { name: 'Bhopal – Itarsi', code: 'BPL – ET', availability: 97.8, trains: 42, status: 'On track', color: 'green' },
    { name: 'Bina – Bhopal', code: 'BINA – BPL', availability: 94.2, trains: 36, status: 'Watch', color: 'amber' },
    { name: 'Itarsi – Jabalpur', code: 'ET – JBP', availability: 98.6, trains: 28, status: 'On track', color: 'green' },
    { name: 'Bhopal – Nagpur', code: 'BPL – NGP', availability: 91.5, trains: 31, status: 'At risk', color: 'red' },
  ],
  history: fallbackHistory,
  alerts: [
    { id: 'ALT-001', asset: 'Rail fracture inspection', location: 'KM 142/6 · BPL–ET', department: 'Engineering', priority: 'Critical', age_minutes: 18, open: true },
    { id: 'ALT-002', asset: 'Signal relay failure', location: 'Itarsi Jn · Panel B', department: 'S&T', priority: 'Critical', age_minutes: 7, open: true },
    { id: 'ALT-003', asset: 'OHE insulator degradation', location: 'KM 88/3 · BINA–BPL', department: 'Traction', priority: 'High', age_minutes: 42, open: true },
  ],
  integrations: ['TMS', 'SMMS', 'TDMS', 'COA', 'BDMS'].map((system) => ({ system, status: 'Simulated', latency_ms: 80 })),
  ingestion_log: [],
}
const fallbackCommand = {
  tasks: fallbackTasks.map((task) => ({ ...task, zone: 'Bhopal Division', asset_type: task.department === 'Engineering' ? 'Track' : task.department === 'S&T' ? 'Signal' : 'OHE', overdue: task.due.includes('Overdue') })),
  blocks: fallbackBlocks,
  workload: { Engineering: { tasks: 2, overdue: 1 }, 'S&T': { tasks: 2, overdue: 0 }, Traction: { tasks: 2, overdue: 0 } },
  clusters: [],
  block_utilization: 78,
  projected_availability: 98,
  joint_requests: [],
}
const badgeClass = (value) => `badge ${String(value).toLowerCase().replace(/[^a-z]+/g, '-')}`
const currentDateLabel = new Intl.DateTimeFormat('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(new Date())
const formatChange = (value, unit = '') => value === 0 ? 'steady' : `${value > 0 ? '+' : '−'}${Math.abs(value).toFixed(unit === ' pts' ? 1 : 0)}${unit}`

function App() {
  const [page, setPage] = useState('Overview')
  const [darkMode, setDarkMode] = useState(() => window.localStorage.getItem('railcode-theme') === 'dark')
  const [tasks, setTasks] = useState(fallbackTasks)
  const [blocks, setBlocks] = useState(fallbackBlocks)
  const [simulation, setSimulation] = useState(fallbackSimulation)
  const [command, setCommand] = useState(fallbackCommand)
  const [connected, setConnected] = useState(false)
  const [horizon, setHorizon] = useState('This week')
  const [horizonDays, setHorizonDays] = useState(7)
  const [filter, setFilter] = useState('All departments')
  const [zoneFilter, setZoneFilter] = useState('All divisions')
  const [assetFilter, setAssetFilter] = useState('All asset types')
  const [overdueFilter, setOverdueFilter] = useState('All tasks')
  const [query, setQuery] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(false)
  const [modal, setModal] = useState(false)
  const [coordinationModal, setCoordinationModal] = useState(false)
  const [editTarget, setEditTarget] = useState(null)
  const [selectedBlock, setSelectedBlock] = useState('')
  const [draggedBlock, setDraggedBlock] = useState('')
  const [impact, setImpact] = useState(null)
  const [mobileNav, setMobileNav] = useState(false)

  useEffect(() => {
    document.documentElement.dataset.theme = darkMode ? 'dark' : 'light'
    window.localStorage.setItem('railcode-theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

  const refresh = useCallback(async () => {
    try {
      const response = await fetch(`${API}/api/command`)
      if (!response.ok) throw new Error('The planning service returned an error.')
      const data = await response.json()
      setCommand(data)
      setTasks(data.tasks)
      setBlocks(data.blocks)
      setSimulation(data.simulation)
      setConnected(true)
    } catch {
      setConnected(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    let socket
    let retry
    let active = true
    const connect = () => {
      if (!active) return
      const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
      socket = new WebSocket(`${scheme}://${window.location.host}/ws/updates`)
      socket.onopen = () => setConnected(true)
      socket.onmessage = (event) => {
        const update = JSON.parse(event.data)
        if (update.type === 'simulation') {
          setSimulation(update.data)
          setCommand((current) => ({
            ...current,
            simulation: update.data,
            projected_availability: Math.min(99.5, update.data.network_availability + 1.6),
          }))
        }
        else if (update.type === 'refresh') refresh()
      }
      socket.onclose = () => {
        if (active) { setConnected(false); retry = window.setTimeout(connect, 3000) }
      }
      socket.onerror = () => socket.close()
    }
    connect()
    return () => { active = false; window.clearTimeout(retry); socket?.close() }
  }, [refresh])

  useEffect(() => {
    if (!notice) return undefined
    const timeout = window.setTimeout(() => setNotice(''), 4000)
    return () => window.clearTimeout(timeout)
  }, [notice])

  const visibleTasks = useMemo(() => tasks.filter((task) =>
    (filter === 'All departments' || task.department === filter) &&
    (zoneFilter === 'All divisions' || task.zone === zoneFilter) &&
    (assetFilter === 'All asset types' || task.asset_type === assetFilter) &&
    (overdueFilter === 'All tasks' || (overdueFilter === 'Overdue only' ? task.overdue : !task.overdue)) &&
    `${task.id} ${task.asset} ${task.location} ${task.corridor}`.toLowerCase().includes(query.toLowerCase()),
  ), [tasks, filter, zoneFilter, assetFilter, overdueFilter, query])
  const timelineDates = useMemo(() => Array.from({ length: horizonDays }, (_, index) => {
    const day = new Date()
    day.setHours(12, 0, 0, 0)
    day.setDate(day.getDate() + index)
    return { iso: day.toISOString().slice(0, 10), day: new Intl.DateTimeFormat('en-IN', { weekday: 'short' }).format(day), date: day.getDate() }
  }), [horizonDays])

  async function generatePlan() {
    setLoading(true)
    try {
      const response = await fetch(`${API}/api/plan/generate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ horizon }),
      })
      if (!response.ok) throw new Error('Schedule generation failed.')
      const result = await response.json()
      setBlocks(result.blocks)
      setTasks(result.tasks)
      setCommand((current) => ({ ...current, blocks: result.blocks, tasks: result.tasks }))
      await refresh()
      setNotice(`Optimized ${result.blocks.length} block windows · ${result.tasks_scheduled} tasks coordinated`)
    } catch {
      setNotice('Unable to reach the planner. Start the backend service and try again.')
    } finally {
      setLoading(false)
    }
  }

  async function controlSimulation(action, speed) {
    try {
      const response = await fetch(`${API}/api/demo/control`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, ...(speed ? { speed } : {}) }),
      })
      if (!response.ok) throw new Error('The simulation control request failed.')
      setSimulation(await response.json())
    } catch {
      setNotice('Unable to control the demo simulation. Check that the backend service is running.')
    }
  }

  async function moveBlock(blockId, startTime, dateIso) {
    try {
      const response = await fetch(`${API}/api/blocks/${encodeURIComponent(blockId)}/what-if`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ start_time: startTime, date_iso: dateIso }),
      })
      if (!response.ok) throw new Error('The what-if request failed.')
      const result = await response.json()
      setImpact(result)
      setBlocks((current) => current.map((block) => block.id === blockId ? result.block : block))
      setCommand((current) => ({ ...current, blocks: current.blocks.map((block) => block.id === blockId ? result.block : block) }))
      setNotice(`What-if impact recalculated for ${startTime} · ${dateIso}.`)
    } catch {
      setNotice('Unable to move this demo block. Check that the planning API is connected.')
    }
  }

  async function submitJointRequest(event) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const departments = form.getAll('departments')
    const taskIds = form.getAll('task_ids')
    const resourcesConfirmed = form.get('resources_confirmed') === 'on'
    try {
      const response = await fetch(`${API}/api/blocks/${encodeURIComponent(form.get('block_id'))}/joint-request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ departments, task_ids: taskIds, resources_confirmed: resourcesConfirmed }),
      })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Joint-block request failed.')
      setCommand((current) => ({ ...current, joint_requests: [result, ...current.joint_requests] }))
      setCoordinationModal(false)
      setNotice(`Joint request ${result.id} created · ${result.status.toLowerCase()}`)
    } catch (error) {
      setNotice(error.message || 'Unable to create the joint-block request.')
    }
  }

  async function proposeEmergency(alert) {
    try {
      const response = await fetch(`${API}/api/alerts/${encodeURIComponent(alert.id)}/emergency-block`, { method: 'POST' })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Emergency block proposal failed.')
      setBlocks((current) => [...current.filter((block)=>block.id!==result.block.id), result.block])
      setCommand((current) => ({ ...current, blocks: [...current.blocks.filter((block)=>block.id!==result.block.id),result.block] }))
      setSelectedBlock(result.block.id)
      setHorizonDays(7)
      setHorizon('This week')
      setPage('Block planner')
      setNotice(`Sample emergency block ${result.block.id} proposed · authorized approval required`)
    } catch (error) {
      setNotice(error.message || 'Unable to propose an emergency block.')
    }
  }

  async function proposeCluster(cluster) {
    if (!blocks.length) {
      setNotice('Generate a sample block schedule before proposing a task cluster.')
      return
    }
    setSelectedBlock(blocks.find((block) => block.corridor === cluster.corridor)?.id || blocks[0].id)
    setCoordinationModal(true)
  }

  async function saveTaskChanges(event) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const task = Object.fromEntries(form.entries())
    task.duration = Number(task.duration)
    task.criticality = Number(task.criticality)
    try {
      const response = await fetch(`${API}/api/tasks/${encodeURIComponent(editTarget.data.id)}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(task),
      })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Task update failed.')
      await refresh()
      setEditTarget(null)
      setNotice(`Controller update saved for ${result.id} · synchronized to connected dashboards.`)
    } catch (error) {
      setNotice(error.message || 'Unable to save the maintenance task changes.')
    }
  }

  async function saveBlockChanges(event) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const block = {
      corridor: form.get('corridor'),
      section: form.get('section'),
      date_iso: form.get('date_iso'),
      start_time: form.get('start_time'),
      duration: Number(form.get('duration')),
      departments: form.getAll('departments'),
      tasks: Number(form.get('tasks')),
      status: form.get('status'),
      trains: Number(form.get('trains')),
      availability: Number(form.get('availability')),
      resources: {
        manpower: form.get('resource_manpower'),
        machines: form.get('resource_machines'),
        materials: form.get('resource_materials'),
      },
      confidence: Number(form.get('confidence')),
      reasoning: form.get('reasoning'),
    }
    try {
      const response = await fetch(`${API}/api/blocks/${encodeURIComponent(editTarget.data.id)}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(block),
      })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Block update failed.')
      await refresh()
      setEditTarget(null)
      setNotice(result.conflicting_blocks.length
        ? `Controller update saved and synchronized · review same-corridor overlap with ${result.conflicting_blocks.join(', ')}.`
        : `Controller update saved for ${result.block.id} · synchronized to connected dashboards. Approval is still required.`)
    } catch (error) {
      setNotice(error.message || 'Unable to save the block changes.')
    }
  }

  function dropOnTimeline(event, dateIso) {
    event.preventDefault()
    const blockId = event.dataTransfer.getData('text/plain') || draggedBlock
    const rect = event.currentTarget.getBoundingClientRect()
    const fraction = Math.min(0.999, Math.max(0, (event.clientX - rect.left) / rect.width))
    const minuteOfDay = Math.round(fraction * 96) * 15
    const startTime = `${String(Math.floor(minuteOfDay / 60)).padStart(2, '0')}:${String(minuteOfDay % 60).padStart(2, '0')}`
    const block = blocks.find((item) => item.id === blockId)
    if (block) void moveBlock(blockId, startTime, dateIso)
    setDraggedBlock('')
    setImpact(null)
  }

  const overrideBlock = blocks.find((block) => block.id === selectedBlock) || blocks[0]

  async function createTask(event) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const task = {
      asset: form.get('asset'), location: form.get('location'), department: form.get('department'),
      corridor: form.get('corridor'), duration: Number(form.get('duration')), priority: form.get('priority'),
    }
    try {
      const response = await fetch(`${API}/api/tasks`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(task),
      })
      if (!response.ok) throw new Error('Task creation failed.')
      await response.json()
      await refresh()
      setModal(false)
      setNotice('Maintenance task added to the planning queue.')
    } catch {
      const localTask = { ...task, id: `LOCAL-${Date.now().toString().slice(-4)}`, source: 'Manual', due: 'Just added', status: 'Unscheduled', criticality: 58 }
      setTasks((existing) => [localTask, ...existing])
      setModal(false)
      setNotice('Task added locally. Connect the planning service to persist it.')
    }
  }

  function exportPlan() {
    const csv = ['Block ID,Corridor,Section,Window,Duration (hrs),Departments,Tasks,Status',
      ...blocks.map((block) => [block.id, block.corridor, block.section, block.date, block.duration, block.departments.join(' + '), block.tasks, block.status].map((item) => `"${String(item).replaceAll('"', '""')}"`).join(','))].join('\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = 'railcode-block-schedule.csv'
    link.click()
    URL.revokeObjectURL(url)
    setNotice('Block schedule exported as CSV.')
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
        <div className="brand"><div className="brand-mark"><TrainFront size={21} strokeWidth={2.2} /></div><div><strong className="brand-name">RAILCODE</strong><small>OPERATIONS CONTROL</small></div></div>
        <div className="rail-label">WORKSPACE</div>
        <nav className="nav-list" aria-label="Main navigation">
          {NAV.map(({ id, icon: Icon }) => <button key={id} className={`nav-link ${page === id ? 'active' : ''}`} onClick={() => { setPage(id); setMobileNav(false) }}><Icon size={18} /><span>{id}</span>{id === 'Maintenance' && <span className="nav-count">{tasks.length}</span>}</button>)}
        </nav>
        <div className="network-card">
          <div className="network-heading"><span className={`status-dot ${simulation.running ? 'online' : ''}`} /><span>{simulation.running ? 'Demo simulation running' : 'Simulation paused'}</span></div>
          <div className="network-systems"><span><i className="system-dot simulated" />TMS</span><span><i className="system-dot simulated" />SMMS</span><span><i className="system-dot simulated" />TDMS</span><span><i className="system-dot simulated" />COA</span></div>
          <div className="network-note">{connected ? 'Synthetic feeds · WebSocket' : 'Sample snapshot · API offline'}</div>
        </div>
        <div className="sidebar-bottom">
          <div className="profile"><div className="avatar">AC</div><div className="profile-info"><strong>Arjun Chatterjee</strong><small>Divisional controller</small></div></div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <button className="mobile-menu icon-button" aria-label="Open navigation" onClick={() => setMobileNav(!mobileNav)}><Menu size={20} /></button>
          <div className="breadcrumbs">Operations <ChevronRight size={14} /> <strong>{page}</strong></div>
          <div className="topbar-actions"><span className="division-chip"><span className="status-dot online" /> Bhopal Division</span><button className="theme-toggle" type="button" onClick={() => setDarkMode((enabled) => !enabled)} aria-label={`Switch to ${darkMode ? 'light' : 'dark'} mode`} title={`Switch to ${darkMode ? 'light' : 'dark'} mode`}>{darkMode ? <Sun size={17} /> : <Moon size={17} />}<span>{darkMode ? 'Light mode' : 'Dark mode'}</span></button><div className="topbar-date"><CalendarDays size={16} /> {currentDateLabel}</div></div>
        </header>
        <div className="content">
          <div className="page-title-row">
            <div><div className="eyebrow"><span className={`live-pill ${simulation.running ? '' : 'paused'}`}><span /> SIMULATION {simulation.running ? 'RUNNING' : 'PAUSED'}</span><span className="demo-label">NO LIVE RAILWAY DATA</span></div><h1>{page === 'Overview' ? 'Unified command dashboard' : page}</h1><p className="page-subtitle">{page === 'Overview' ? 'Explore the simulated network, block efficiency, urgent defects, and cross-department work.' : page === 'Block planner' ? 'Coordinate sample maintenance windows across corridors and departments.' : page === 'Maintenance' ? 'Explore sample defects and planned work from simulated feeds.' : page === 'Corridors' ? 'Explore simulated corridor availability and train movements.' : page === 'System health' ? 'Inspect synthetic feed connectivity and generated model-ingestion events.' : page === 'Coordination hub' ? 'Coordinate shared sample possessions, departments, and resource readiness.' : 'Explore simulated availability and maintenance planning trends.'}</p></div>
            {page === 'Block planner' && <div className="title-actions"><button className="button button-light" onClick={exportPlan}><Download size={16} /> Export schedule</button><button className="button button-primary" onClick={generatePlan} disabled={loading}><Sparkles size={16} className={loading ? 'spin' : ''} />{loading ? 'Optimizing…' : 'Generate plan'}</button></div>}
          </div>

          {page === 'Overview' && <div className="integration-strip"><div className="integration-icon"><Activity size={17} /></div><span><strong>Demo data</strong> · Simulated railway feeds only. No live railway systems are connected.</span><span className="strip-separator" /><span className="simulation-controls"><span className="strip-right"><span className={`status-dot ${connected ? 'online' : ''}`} />{connected ? 'Connected' : 'API offline'}</span><button className="sim-control" onClick={() => controlSimulation(simulation.running ? 'pause' : 'resume')} disabled={!connected} title={simulation.running ? 'Pause simulated changes' : 'Resume simulated changes'}>{simulation.running ? <Pause size={12} /> : <Play size={12} />}{simulation.running ? 'Pause demo' : 'Resume demo'}</button></span></div>}

          {['Overview', 'Analytics'].includes(page) && <section className="metrics-grid">
            <Metric icon={Gauge} label="Asset uptime · current" value={`${simulation.network_availability.toFixed(1)}%`} change={formatChange(simulation.changes.network_availability, ' pts')} tone={simulation.changes.network_availability >= 0 ? 'good' : 'caution'} foot="synthetic · updates every 2 sec" accent="blue" />
            <Metric icon={Blocks} label="Simulated blocks" value={String(simulation.blocks_scheduled).padStart(2, '0')} change={formatChange(simulation.changes.blocks_scheduled)} tone="neutral" foot="scenario · 4 sample corridors" accent="violet" />
            <Metric icon={Wrench} label="Coordinated work" value={String(simulation.tasks_coordinated).padStart(2, '0')} change={formatChange(simulation.changes.tasks_coordinated)} tone="neutral" foot="simulated maintenance volume" accent="teal" />
            <Metric icon={ShieldCheck} label="Projected uptime" value={`${Math.min(99.5,simulation.network_availability+1.6).toFixed(1)}%`} change="+1.6 pts" tone="good" foot="illustrative · plan acceptance assumed" accent="amber" />
          </section>}

          {['Overview', 'Analytics'].includes(page) && <section className={`dashboard-grid ${page === 'Overview' ? 'overview-dashboard' : 'analytics-dashboard'}`}>
            <div className="card availability-card">
              <div className="card-heading"><div><div className="section-kicker">SIMULATED NETWORK PERFORMANCE</div><h2>Asset availability</h2><p>Illustrative service availability · not live railway telemetry</p></div></div>
              <div className="chart-summary"><strong>{simulation.network_availability.toFixed(1)}<span>%</span></strong><span className={`change-chip ${simulation.changes.network_availability < 0 ? 'negative' : ''}`}>{simulation.changes.network_availability > 0 ? <ArrowUpRight size={14} /> : simulation.changes.network_availability < 0 ? <ArrowDownRight size={14} /> : null}{formatChange(simulation.changes.network_availability, ' pts')}</span><span className="summary-period">since previous simulation tick</span></div>
              <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={simulation.history} margin={{ top: 14, right: 8, left: -24, bottom: 0 }}><defs><linearGradient id="availabilityGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#4678ec" stopOpacity={0.2} /><stop offset="95%" stopColor="#4678ec" stopOpacity={0} /></linearGradient></defs><CartesianGrid vertical={false} stroke="#edf0f5" strokeDasharray="4 5" /><XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: '#8a94a7', fontSize: 11, fontFamily: 'DM Sans' }} dy={10} /><YAxis domain={[88, 100]} axisLine={false} tickLine={false} ticks={[90, 95, 100]} tickFormatter={(value) => `${value}%`} tick={{ fill: '#8a94a7', fontSize: 10, fontFamily: 'DM Sans' }} /><Tooltip content={<ChartTooltip />} /><Area type="monotone" dataKey="availability" stroke="#4c78e8" strokeWidth={2.5} fill="url(#availabilityGradient)" dot={{ r: 3, fill: '#fff', stroke: '#4c78e8', strokeWidth: 2 }} activeDot={{ r: 5 }} /></AreaChart></ResponsiveContainer></div>
              <div className="chart-legend"><span><i className="legend-line" />Simulated availability</span><span><i className="legend-dash" />Illustrative 95% target</span><span className="chart-note"><Radio size={14} /> Updates every 2 sec</span></div>
            </div>

          </section>}

          {page === 'Corridors' && <section className="corridor-page-grid">
            <div className="card corridor-card">
              <div className="card-heading"><div><div className="section-kicker">SIMULATED CORRIDOR STATUS</div><h2>Availability by route</h2><p>Sample train counts · continuously changing</p></div></div>
              <div className="corridor-list">
                {simulation.corridors.map((corridor) => <Corridor key={corridor.code} {...corridor} />)}
              </div>
              <div className="corridor-page-note">Train volumes, availability and status are continuously simulated for this demo.</div>
            </div>
          </section>}

          {page === 'Overview' && <section className="command-grid">
            <div className="card alert-card"><div className="section-header"><div><div className="section-kicker">SAFETY · SIMULATED FEED</div><h2>Critical alerts</h2></div><span className="alert-count">{simulation.alerts?.length || 0} open</span></div><div className="alert-list">{(simulation.alerts || []).slice(0, 4).map((alert) => <div className="alert-row" key={alert.id}><div className={`alert-icon ${alert.priority === 'Critical' ? 'critical' : ''}`}><AlertTriangle size={16} /></div><div className="alert-main"><strong>{alert.asset}</strong><span>{alert.location} · {alert.department}</span></div><div className="alert-age"><span className={badgeClass(alert.priority)}>{alert.priority}</span><small>{alert.age_minutes} min ago</small><button className="alert-action" onClick={()=>proposeEmergency(alert)}>Propose block</button></div></div>)}</div><p className="panel-disclaimer">Illustrative emergency alerts only · proposals require authorized approval.</p></div>
            <div className="card workload-card"><div className="section-header"><div><div className="section-kicker">OPEN SAMPLE WORK</div><h2>Department workload</h2></div><span className="sample-tag">SIMULATED</span></div><WorkloadBreakdown workload={command.workload} /><div className="workload-legend">{[['Engineering','blue'],['S&T','purple'],['Traction','teal']].map(([name,color])=><span key={name}><i className={color}/>{name} <b>{command.workload?.[name]?.tasks || 0}</b></span>)}</div></div>
            <div className="card utilization-card"><div className="section-header"><div><div className="section-kicker">PLANNING EFFICIENCY</div><h2>Block utilization</h2></div><span className="sample-tag">DEMO</span></div>            <div className="utilization-content"><div className="utilization-gauge" style={{'--utilization':`${simulation.block_utilization}%`}}><div><strong>{simulation.block_utilization}%</strong><small>sample blocks used</small></div></div><div className="utilization-details"><div><span>Critical assets</span><strong>{simulation.critical_asset_availability.toFixed(1)}%</strong></div><div><span>Current network</span><strong>{simulation.network_availability.toFixed(1)}%</strong></div><div><span>Projected network</span><strong>{Math.min(99.5,simulation.network_availability+1.6).toFixed(1)}%</strong></div></div></div><p className="panel-disclaimer">Synthetic utilization indicator · not a live BDMS statistic.</p></div>
          </section>}

          {page === 'Block planner' && <section className="card gantt-card">
            <div className="gantt-header"><div><div className="section-kicker">TRAFFIC + POSSESSION TIMELINE</div><h2>{horizonDays === 7 ? 'Tactical plan · next 7 days' : 'Strategic plan · next 30 days'}</h2><p>Illustrative passenger and freight paths alongside proposed maintenance windows</p></div><div className="horizon-toggle" role="group" aria-label="Planning time horizon"><button className={horizonDays === 7 ? 'selected' : ''} onClick={() => { setHorizonDays(7); setHorizon('This week') }}>Next 7 days</button><button className={horizonDays === 30 ? 'selected' : ''} onClick={() => { setHorizonDays(30); setHorizon('This month') }}>Next 30 days</button></div></div>
            <div className="timeline-legend"><span><i className="train-passenger" /> Passenger train traffic</span><span><i className="train-freight" /> Goods train forecast</span><span><i className="block-legend" /> Proposed maintenance · drag to override</span></div>
            <div className="gantt-scroller"><div className="gantt-grid" style={{'--day-count':horizonDays,'--day-width':horizonDays === 7 ? '128px' : '92px'}}><div className="gantt-corner">CORRIDOR</div>{timelineDates.map((day) => <div className="gantt-day-head" key={day.iso}><span>{day.day}</span><strong>{day.date}</strong></div>)}
              {simulation.corridors.map((corridor,index) => <Fragment key={corridor.code}><div className="gantt-route"><strong>{corridor.code.replaceAll(' ','')}</strong><span>{corridor.name}</span></div>{timelineDates.map((day,dayIndex) => {
                const blocksToday = blocks.filter((block,blockIndex) => block.corridor === corridor.code.replaceAll(' ','') && (block.date_iso || dayIndexForBlock(block,blockIndex,timelineDates)) === day.iso)
                return <div className="gantt-cell" key={`${corridor.code}-${day.iso}`} onDragOver={(event) => event.preventDefault()} onDrop={(event) => dropOnTimeline(event,day.iso)}><i className="traffic-band passenger-band" style={{left:`${8+(dayIndex%4)*4}%`,width:`${17+(index%2)*4}%`}}/><i className="traffic-band freight-band" style={{left:`${70-(dayIndex%3)*4}%`,width:'18%'}}/>{blocksToday.map((block) => <button key={block.id} className={`gantt-block ${draggedBlock === block.id ? 'dragging' : ''}`} draggable onDragStart={(event) => {event.dataTransfer.setData('text/plain',block.id);setDraggedBlock(block.id)}} onDragEnd={() => setDraggedBlock('')} onClick={() => setSelectedBlock(block.id)} title={`${block.id}: ${block.window} · ${block.departments.join(' + ')}`} style={{left:`${timePercent(block.window)}%`,width:`${Math.max(17,Math.min(91,block.duration/24*100))}%`}}><span>{block.window.split('–')[0].trim()}</span><Wrench size={10}/></button>)}</div>
              })}</Fragment>)}</div></div>
            <div className="timeline-scale"><span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>24:00</span><span>Drag a block within a day to run a what-if</span></div>
              {overrideBlock && <form key={`${overrideBlock.id}-${overrideBlock.date_iso}-${overrideBlock.window}`} className="manual-override" onSubmit={(event)=>{event.preventDefault();const data=new FormData(event.currentTarget);void moveBlock(data.get('block_id'),data.get('start_time'),data.get('date_iso'))}}><strong>Manual what-if override</strong><label>Block<select name="block_id" value={overrideBlock.id} onChange={(event)=>setSelectedBlock(event.target.value)}>{blocks.map((block)=><option key={block.id} value={block.id}>{block.id} · {block.corridor}</option>)}</select></label><label>New date<input name="date_iso" type="date" defaultValue={overrideBlock.date_iso || timelineDates[0]?.iso} required/></label><label>New start time<input name="start_time" type="time" defaultValue={overrideBlock.window.slice(0,5)} required/></label><button className="button button-outline" type="submit"><SlidersHorizontal size={14}/>Recalculate impact</button></form>}
              <div className="plan-detail-grid"><div className="reasoning-card"><div className="reasoning-icon"><Sparkles size={16}/></div><div><div className="section-kicker">AI PLANNER · EXPLAINABLE DEMO HEURISTIC</div><h3>{(blocks.find((block)=>block.id===selectedBlock)||blocks[0])?.id || 'Generate a plan to start'}</h3><p>{(blocks.find((block)=>block.id===selectedBlock)||blocks[0])?.reasoning || 'Generate an illustrative maintenance schedule to inspect its reasoning.'} All train impact, confidence, and windows are simulated.</p></div><div className="confidence-ring" style={{'--confidence':`${(blocks.find((block)=>block.id===selectedBlock)||blocks[0])?.confidence || 0}%`}}><strong>{(blocks.find((block)=>block.id===selectedBlock)||blocks[0])?.confidence || 0}%</strong><span>confidence</span></div></div>
              <div className="resource-inline"><span><b>RESOURCES</b> · don't grant a block until each work group is ready.</span>{Object.entries((blocks.find((block)=>block.id===selectedBlock)||blocks[0])?.resources || {}).map(([resource,status])=><span key={resource} className={`resource-chip ${status.toLowerCase()}`}><i/>{resource}: {status}</span>)}</div>
              {(blocks.find((block)=>block.id===selectedBlock)||blocks[0]) && <button className="button button-outline controller-edit-button" onClick={()=>setEditTarget({type:'block',data:blocks.find((block)=>block.id===selectedBlock)||blocks[0]})}><Pencil size={14}/> Edit block details</button>}
            </div>
            {impact && <div className="whatif-impact"><AlertTriangle size={17}/><div><strong>What-if impact · estimated {impact.impact.estimated_delay_minutes} minutes total delay</strong><span>{impact.impact.passenger_trains_delayed} passenger + {impact.impact.freight_trains_delayed} goods trains potentially affected · {impact.impact.reason}</span></div><button aria-label="Dismiss what-if result" onClick={()=>setImpact(null)}><X size={15}/></button></div>}
          </section>}

          {['Coordination hub', 'System health'].includes(page) && <section className={`coordination-grid ${page === 'System health' ? 'health-grid' : 'coordination-page-grid'}`}>
            {page === 'Coordination hub' && <div className="card cluster-card"><div className="section-header"><div><div className="section-kicker">AI-ASSISTED COORDINATION</div><h2>Nearby task clusters</h2></div><span className="sample-tag">SAME-CORRIDOR DEMO</span></div>{command.clusters?.length ? command.clusters.map((cluster)=><div className="cluster-row" key={cluster.corridor}><div className="cluster-route"><Map size={16}/></div><div className="cluster-main"><strong>{cluster.corridor} · {cluster.count} tasks in a sample corridor</strong><span>{cluster.departments.join(' + ')} · {cluster.critical} high/critical · {cluster.proximity_method}</span></div><div className="cluster-save">~{cluster.saving_hours}h<br/>block saved*</div><button className="button button-outline" onClick={()=>proposeCluster(cluster)}>Build joint block <ArrowRight size={13}/></button></div>):<div className="empty-clusters">Generate task clusters from same-corridor maintenance activity.</div>}{command.joint_requests?.length>0&&<div className="request-summary">{command.joint_requests.slice(0,3).map((request)=><span key={request.id}><CheckCircle2 size={14}/>{request.id} · {request.status}</span>)}</div>}<div className="coordination-footer"><button className="button button-primary" onClick={()=>{setSelectedBlock(blocks[0]?.id || '');setCoordinationModal(true)}}><Plus size={15}/> Initiate joint block</button><span>Piggyback tasks from other departments into a shared corridor possession.</span></div></div>}
            {page === 'System health' && <div className="card integration-health-card"><div className="section-header"><div><div className="section-kicker">CONNECTIVITY &amp; MODEL INGESTION</div><h2>External system connections</h2></div><span className="sample-tag">NO LIVE CONNECTIONS</span></div><div className="integration-list">{(simulation.integrations||[]).map((item)=><div key={item.system} className="integration-row"><span className="integration-system">{item.system}</span><span className="sim-status-dot"/><span className="simulation-only">SIMULATED</span><span className="external-offline-dot"/><span className="external-label">{item.external_status || 'Not connected'}</span><span className="latency">{item.latency_ms} ms</span></div>)}</div><div className="integration-disclaimer">Colored indicators distinguish synthetic demo feeds from external railway systems, which remain disconnected.</div></div>}
          </section>}

          {page === 'System health' && <section className="card ingestion-card"><div className="section-header"><div><div className="section-kicker">SYNTHETIC DATA PIPELINE</div><h2>Recent demo ingestion</h2></div><span className="sample-tag">UPDATED {new Date(simulation.sampled_at).toLocaleTimeString('en-IN')}</span></div><div className="ingestion-list">{(simulation.ingestion_log||[]).map((entry,index)=><div className="ingestion-row" key={`${entry.system}-${entry.sampled_at}`}><span className="ingestion-pulse"/><strong>{entry.system}</strong><span>{entry.event}</span><time>{new Date(entry.sampled_at).toLocaleTimeString('en-IN')}</time><span className="simulated-badge">SIMULATED</span></div>)}</div><div className="integration-disclaimer">Generated demo events only; these are not records of connections to TMS, SMMS, TDMS, COA or BDMS.</div></section>}

          {page === 'Maintenance' && <section className="card work-card">
            <div className="work-header"><div><div className="section-kicker">MAINTENANCE COORDINATION · SAMPLE RECORDS</div><h2>{page === 'Maintenance' ? 'Unified defect & maintenance backlog' : 'Priority maintenance tasks'}</h2><p>AI-assessed criticality · simulated records from TMS, SMMS &amp; TDMS</p></div><div className="work-actions"><label className="search-box"><Search size={16} /><input id="task-search" placeholder="Search tasks…" value={query} onChange={(event) => setQuery(event.target.value)} /></label><button className="button button-outline add-button" onClick={() => setModal(true)}><Plus size={16} /> Add task</button></div></div>
            <div className="advanced-filters"><select className="filter-select" value={filter} onChange={(event) => setFilter(event.target.value)} aria-label="Filter department"><option>All departments</option><option>Engineering</option><option>S&amp;T</option><option>Traction</option></select><select className="filter-select" value={zoneFilter} onChange={(event) => setZoneFilter(event.target.value)} aria-label="Filter division"><option>All divisions</option><option>Bhopal Division</option></select><select className="filter-select" value={assetFilter} onChange={(event) => setAssetFilter(event.target.value)} aria-label="Filter asset type"><option>All asset types</option><option>Track</option><option>Signal</option><option>OHE</option></select><select className="filter-select" value={overdueFilter} onChange={(event) => setOverdueFilter(event.target.value)} aria-label="Filter overdue work"><option>All tasks</option><option>Overdue only</option><option>Not overdue</option></select><span className="filter-result-count">{visibleTasks.length} matching sample tasks</span></div>
            <div className="table-scroll"><table><thead><tr><th>MAINTENANCE ACTIVITY</th><th>DEPARTMENT</th><th>PRIORITY</th><th>AI CRITICALITY</th><th>TARGET</th><th>DURATION</th><th>PLAN STATUS</th><th /></tr></thead><tbody>
              {visibleTasks.length === 0 && <tr><td colSpan="8" className="empty-state">No tasks match your filters.</td></tr>}
              {visibleTasks.slice(0, page === 'Maintenance' ? undefined : 5).map((task) => <tr key={task.id}><td><div className="task-name">{task.asset}</div><div className="task-location"><span className="task-id">{task.id}</span><span>·</span>{task.location}</div></td><td><span className={`department ${task.department === 'Engineering' ? 'engineering' : task.department === 'S&T' ? 'signalling' : 'traction'}`}><span />{task.department}</span><div className="source-label">sample · {task.source}</div></td><td><span className={badgeClass(task.priority)}><i />{task.priority}</span></td><td><CriticalityScore score={task.criticality} /></td><td><span className={`due-date ${task.overdue ? 'overdue' : ''}`}>{task.overdue && <AlertTriangle size={13} />}{task.due}</span></td><td><span className="duration">{task.duration} hrs</span></td><td><span className={badgeClass(task.status)}>{task.status === 'Scheduled' ? <Check size={12} /> : <Clock3 size={12} />}{task.status}</span></td><td><button className="row-more" aria-label={`Edit ${task.id}`} title={`Edit ${task.id}`} onClick={() => setEditTarget({type:'task',data:task})}><Pencil size={16} /></button></td></tr>)}
            </tbody></table></div>
            <div className="table-footer"><span>{visibleTasks.length} matching maintenance tasks</span></div>
          </section>}

          {page === 'Overview' && <section className="bottom-grid overview-blocks">
            <div className="card blocks-card"><div className="card-heading"><div><div className="section-kicker">UPCOMING PROPOSALS</div><h2>Next block windows</h2><p>Sample schedule · approval required</p></div><button className="text-link" onClick={() => setPage('Block planner')}>Open planner <ArrowRight size={14} /></button></div>
              <div className="block-list">{blocks.slice(0, 3).map((block) => <div className="block-row" key={block.id}><div className={`block-date-icon ${block.status === 'Confirmed' ? 'confirmed' : ''}`}><CalendarDays size={17} /></div><div className="block-main"><div className="block-title">{block.corridor} <span>·</span> {block.section}</div><div className="block-meta"><Clock3 size={13} />{block.date}{block.departments.map((department) => <span key={department} className="department-tag">{department}</span>)}</div></div><div className="block-impact"><strong>{block.duration}h</strong><small>{block.tasks} task{block.tasks === 1 ? '' : 's'}</small></div><span className={badgeClass(block.status)}>{block.status}</span></div>)}</div>
            </div>
          </section>}
          {page !== 'System health' && <footer className="page-footer"><span><ShieldCheck size={14} /> Safety first. All block plans require authorized control office approval.</span><span>RAILCODE <i /> DIVISIONAL OPERATIONS</span></footer>}
        </div>
      </main>
      {mobileNav && <button className="mobile-overlay" aria-label="Close navigation" onClick={() => setMobileNav(false)} />}
      {notice && <div className="toast"><CheckCircle2 size={18} /><span>{notice}</span><button aria-label="Dismiss notification" onClick={() => setNotice('')}><X size={16} /></button></div>}
      {coordinationModal && <div className="modal-backdrop" onClick={(event)=>{if(event.target===event.currentTarget)setCoordinationModal(false)}}><form className="task-modal coordination-modal" onSubmit={submitJointRequest}><div className="modal-heading"><div><div className="section-kicker">CROSS-DEPARTMENT COORDINATION · DEMO</div><h2>Initiate a joint-block request</h2></div><button type="button" className="icon-button" aria-label="Close" onClick={()=>setCoordinationModal(false)}><X size={19}/></button></div><label>Proposed shared block<select name="block_id" value={selectedBlock || blocks[0]?.id || ''} onChange={(event)=>setSelectedBlock(event.target.value)} required>{blocks.map((block)=><option key={block.id} value={block.id}>{block.corridor} · {block.date} · {block.id}</option>)}</select></label><fieldset className="coordination-fieldset"><legend>Primary and piggyback departments</legend><div className="check-grid">{['Engineering','S&T','Traction'].map((department,index)=><label key={department} className="check-option"><input name="departments" type="checkbox" value={department} defaultChecked={index===0}/>{department}{index===0&&<small>Primary</small>}</label>)}</div></fieldset><fieldset className="coordination-fieldset"><legend>Maintenance tasks sharing this corridor</legend><div className="task-check-list">{tasks.filter((task)=>task.corridor===(blocks.find((block)=>block.id===(selectedBlock||blocks[0]?.id))?.corridor)).map((task)=><label key={task.id} className="check-option"><input name="task_ids" type="checkbox" value={task.id} defaultChecked={task.priority==='Critical'||task.priority==='High'}/><span>{task.id} · {task.asset}</span><small>{task.department}</small></label>)}</div></fieldset><label className="resource-confirm-option"><input type="checkbox" name="resources_confirmed"/><span><strong>All participating teams confirm readiness</strong><small>Manpower, machines and materials are ready. Leave unchecked to keep the requisition in “resources pending”.</small></span></label><div className="coordination-warning"><AlertTriangle size={15}/>A requisition is a proposal only. It does not request, authorize, or grant a real possession.</div><div className="modal-actions"><button className="button button-light" type="button" onClick={()=>setCoordinationModal(false)}>Cancel</button><button className="button button-primary" type="submit"><Send size={15}/> Submit joint request</button></div></form></div>}
      {editTarget && <div className="modal-backdrop" onClick={(event)=>{if(event.target===event.currentTarget)setEditTarget(null)}}>{editTarget.type === 'task' ? <form key={`task-${editTarget.data.id}`} className="task-modal controller-edit-modal" onSubmit={saveTaskChanges}><div className="modal-heading"><div><div className="section-kicker">DIVISIONAL CONTROLLER · SAVED + SYNCHRONIZED</div><h2>Edit maintenance task · {editTarget.data.id}</h2></div><button type="button" className="icon-button" aria-label="Close" onClick={()=>setEditTarget(null)}><X size={19}/></button></div><label>Activity name<input name="asset" required minLength="3" maxLength="120" defaultValue={editTarget.data.asset}/></label><label>Location<input name="location" required minLength="3" maxLength="120" defaultValue={editTarget.data.location}/></label><div className="form-row"><label>Department<select name="department" defaultValue={editTarget.data.department}>{['Engineering','S&T','Traction'].map((value)=><option key={value}>{value}</option>)}</select></label><label>Source system<input name="source" required minLength="2" maxLength="32" defaultValue={editTarget.data.source}/></label></div><div className="form-row"><label>Corridor<input name="corridor" required minLength="3" maxLength="32" defaultValue={editTarget.data.corridor}/></label><label>Target / due date<input name="due" required minLength="2" maxLength="60" defaultValue={editTarget.data.due}/></label></div><div className="form-row"><label>Priority<select name="priority" defaultValue={editTarget.data.priority}>{['Critical','High','Medium','Low'].map((value)=><option key={value}>{value}</option>)}</select></label><label>Plan status<select name="status" defaultValue={editTarget.data.status}>{['Unscheduled','Scheduled','In progress','Completed','Deferred','Cancelled'].map((value)=><option key={value}>{value}</option>)}</select></label></div><div className="form-row"><label>Duration (hours)<input name="duration" type="number" required min="1" max="12" defaultValue={editTarget.data.duration}/></label><label>Base criticality (1–100)<input name="criticality" type="number" required min="1" max="100" defaultValue={editTarget.data.base_criticality ?? editTarget.data.criticality}/></label></div><div className="coordination-warning"><AlertTriangle size={15}/>Task edits update shared planning data. Criticality remains an illustrative score, not a safety assessment.</div><div className="modal-actions"><button className="button button-light" type="button" onClick={()=>setEditTarget(null)}>Cancel</button><button className="button button-primary" type="submit"><Check size={15}/> Save and synchronize</button></div></form> : <form key={`block-${editTarget.data.id}`} className="task-modal controller-edit-modal" onSubmit={saveBlockChanges}><div className="modal-heading"><div><div className="section-kicker">DIVISIONAL CONTROLLER · SAVED + SYNCHRONIZED</div><h2>Edit block proposal · {editTarget.data.id}</h2></div><button type="button" className="icon-button" aria-label="Close" onClick={()=>setEditTarget(null)}><X size={19}/></button></div><div className="form-row"><label>Corridor<input name="corridor" required minLength="3" maxLength="32" defaultValue={editTarget.data.corridor}/></label><label>Section<input name="section" required minLength="3" maxLength="120" defaultValue={editTarget.data.section}/></label></div><div className="form-row"><label>Date<input name="date_iso" type="date" required defaultValue={editTarget.data.date_iso}/></label><label>Start time<input name="start_time" type="time" required defaultValue={editTarget.data.window.slice(0,5)}/></label></div><div className="form-row"><label>Duration (hours)<input name="duration" type="number" required min="1" max="24" defaultValue={editTarget.data.duration}/></label><label>Status<select name="status" defaultValue={editTarget.data.status}>{['Proposed','Under review','Confirmed','Emergency proposal','Cancelled'].map((value)=><option key={value}>{value}</option>)}</select></label></div><label>Departments holding this block<select name="departments" multiple required defaultValue={editTarget.data.departments}>{['Engineering','S&T','Traction'].map((value)=><option key={value}>{value}</option>)}</select></label><div className="form-row"><label>Task count<input name="tasks" type="number" min="0" max="100" required defaultValue={editTarget.data.tasks}/></label><label>Illustrative trains<input name="trains" type="number" min="0" max="100" required defaultValue={editTarget.data.trains}/></label></div><div className="form-row"><label>Availability estimate (%)<input name="availability" type="number" min="0" max="100" step="0.1" required defaultValue={editTarget.data.availability}/></label><label>Planner confidence (%)<input name="confidence" type="number" min="1" max="100" required defaultValue={editTarget.data.confidence}/></label></div><div className="form-row">{['manpower','machines','materials'].map((resource)=><label key={resource}>{resource[0].toUpperCase()+resource.slice(1)} readiness<select name={`resource_${resource}`} defaultValue={editTarget.data.resources[resource]}>{['Confirmed','Pending','Unavailable'].map((value)=><option key={value}>{value}</option>)}</select></label>)}</div><label>Controller note / reasoning<textarea name="reasoning" required minLength="3" maxLength="500" defaultValue={editTarget.data.reasoning}/></label><div className="coordination-warning"><AlertTriangle size={15}/>Every edited block remains subject to required control-office approval; edits never grant a possession.</div><div className="modal-actions"><button className="button button-light" type="button" onClick={()=>setEditTarget(null)}>Cancel</button><button className="button button-primary" type="submit"><Check size={15}/> Save and synchronize</button></div></form>}</div>}
      {modal && <div className="modal-backdrop" onClick={(event) => { if (event.target === event.currentTarget) setModal(false) }}><form className="task-modal" onSubmit={createTask}><div className="modal-heading"><div><div className="section-kicker">MAINTENANCE REGISTER</div><h2>Add a maintenance task</h2></div><button type="button" className="icon-button" aria-label="Close" onClick={() => setModal(false)}><X size={19} /></button></div><label>Activity name<input name="asset" required placeholder="e.g. Point machine inspection" /></label><label>Location<input name="location" required placeholder="e.g. KM 142/6 · BPL–ET" /></label><div className="form-row"><label>Department<select name="department"><option>Engineering</option><option>S&amp;T</option><option>Traction</option></select></label><label>Corridor<select name="corridor"><option>BPL–ET</option><option>BINA–BPL</option><option>ET–JBP</option><option>BPL–NGP</option></select></label></div><div className="form-row"><label>Priority<select name="priority"><option>High</option><option>Critical</option><option>Medium</option><option>Low</option></select></label><label>Duration (hours)<input name="duration" type="number" required min="1" max="12" defaultValue="2" /></label></div><div className="modal-actions"><button className="button button-light" type="button" onClick={() => setModal(false)}>Cancel</button><button className="button button-primary" type="submit"><Plus size={16} /> Add to queue</button></div></form></div>}
    </div>
  )
}

function Metric({ icon: Icon, label, value, change, tone, foot, accent }) {
  return <div className="metric-card"><div className={`metric-icon ${accent}`}><Icon size={18} /></div><div className="metric-label">{label}</div><div className="metric-value">{value}<span className={`metric-change ${tone}`}>{change === 'steady' ? null : change.startsWith('−') ? <ArrowDownRight size={13} /> : <ArrowUpRight size={13} />}{change}</span></div><div className="metric-foot"><span className="foot-dot" />{foot}</div></div>
}
function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return <div className="chart-tooltip"><strong>{label}</strong><span>{Number(payload[0].value).toFixed(1)}% simulated availability</span></div>
}
function WorkloadBreakdown({ workload }) {
  const values = ['Engineering', 'S&T', 'Traction'].map((department) => workload?.[department]?.tasks || 0)
  const total = values.reduce((sum, value) => sum + value, 0)
  const first = total ? values[0] / total * 100 : 0
  const second = total ? first + values[1] / total * 100 : 0
  return <div className="workload-chart"><div className="workload-donut" style={{background:`conic-gradient(#5179df 0 ${first}%, #9475d1 ${first}% ${second}%, #43a18c ${second}% 100%)`}}><div><strong>{total}</strong><small>open tasks</small></div></div><div className="workload-stats">{['Engineering','S&T','Traction'].map((department,index)=><div key={department}><span className={`workload-bullet ${['blue','purple','teal'][index]}`}/><span>{department} overdue: <b>{workload?.[department]?.overdue||0}</b></span></div>)}</div></div>
}
function CriticalityScore({score}) {
  const tone=score>=80?'high':score>=55?'medium':'low'
  return <span className={`criticality-score ${tone}`} title="Illustrative heuristic score based on sample task priority and defect criticality"><strong>{score}</strong><i><span style={{width:`${score}%`}}/></i></span>
}
function dayIndexForBlock(block,index,dates) {
  return dates[index % dates.length]?.iso || block.date_iso
}
function timePercent(window) {
  const start=window.match(/\d{2}:\d{2}/)?.[0]||'00:30'
  const [hour,minute]=start.split(':').map(Number)
  return (hour*60+minute)/14.4
}
function Corridor({ name, code, availability, trains, status, color }) {
  return <div className="corridor-row"><div className="route-icon"><Radio size={16} /></div><div className="corridor-detail"><div className="corridor-name">{name}<span className="corridor-code">{code}</span></div><div className="corridor-bottom"><span className={`corridor-status ${color}`}><i />{status}</span><span>{trains} simulated trains</span></div></div><div className="corridor-value">{Number(availability).toFixed(1)}<span>%</span><div className="mini-track"><i className={color} style={{ width: `${availability}%` }} /></div></div></div>
}

export default App
