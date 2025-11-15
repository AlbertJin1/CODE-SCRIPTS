// src/supabaseClient.js
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://cnsqlixkahntrzfxkndz.supabase.co'
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNuc3FsaXhrYWhudHJ6ZnhrbmR6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjMxNTQ0MTUsImV4cCI6MjA3ODczMDQxNX0.hhuwWCuhFyEfy5iE4067qHlJf2BKpyTY6Xpqga83srk'

export const supabase = createClient(supabaseUrl, supabaseKey)