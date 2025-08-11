// Универсальный модуль для обработки выбора файла, drag&drop, отправки и прогресса
// Использование:
// new Uploader({
//   form: document.querySelector('#upload-form'),
//   input: document.querySelector('#file-input'),
//   dropzone: document.querySelector('#dropzone'),
//   submitBtn: document.querySelector('#submit-btn'),
//   progressEl: document.querySelector('#progress'),
//   progressBarEl: document.querySelector('#progress .bar'),
//   overlay: document.querySelector('#loading'),
//   endpoint: '/upload',
//   method: 'POST',
//   fieldName: 'file'
// })

(function(){
  function $(sel,root){return (root||document).querySelector(sel)}

  function Uploader(opts){
    this.form = opts.form
    this.input = opts.input
    this.dropzone = opts.dropzone
    this.submitBtn = opts.submitBtn
    this.progressEl = opts.progressEl
    this.progressBarEl = opts.progressBarEl
    this.overlay = opts.overlay
    this.endpoint = opts.endpoint
    this.method = opts.method || 'POST'
    this.fieldName = opts.fieldName || 'file'
    this.onComplete = opts.onComplete || function(){}
    this.onError = opts.onError || function(){}
    this.accept = (this.input && this.input.getAttribute('accept')) || ''

    this._bind()
  }

  Uploader.prototype._bind = function(){
    var self = this

    // drag events
    if(this.dropzone){
      ;['dragenter','dragover'].forEach(function(evt){
        self.dropzone.addEventListener(evt,function(e){
          e.preventDefault(); e.stopPropagation();
          self.dropzone.classList.add('is-dragover')
        })
      })
      ;['dragleave','drop'].forEach(function(evt){
        self.dropzone.addEventListener(evt,function(e){
          e.preventDefault(); e.stopPropagation();
          if(evt==='drop'){
            var files = e.dataTransfer.files
            if(files && files.length) self._setFile(files[0])
          }
          self.dropzone.classList.remove('is-dragover')
        })
      })

      // клики по зоне активируют input
      this.dropzone.addEventListener('click', function(){
        if(self.input) self.input.click()
      })
    }

    if(this.input){
      this.input.addEventListener('change', function(){
        if(self.input.files && self.input.files.length){
          self._setFile(self.input.files[0])
        }
      })
    }

    if(this.form){
      this.form.addEventListener('submit', function(e){
        e.preventDefault()
        self.upload()
      })
    }
  }

  function matchesAccept(file, accept){
    if(!accept) return true
    var types = accept.split(',').map(function(s){return s.trim()}).filter(Boolean)
    if(types.length===0) return true
    return types.some(function(t){
      if(t.endsWith('/*')){
        var prefix = t.slice(0, t.length-1) // keep slash
        return (file.type || '').startsWith(prefix)
      }
      return (file.type || '').toLowerCase() === t.toLowerCase()
    })
  }

  Uploader.prototype._setFile = function(file){
    if(file && !matchesAccept(file, this.accept)){
      this.file = null
      if(this.onError) this.onError({status:0, message:'Неподдерживаемый тип файла: ' + (file.type||'unknown')})
      return
    }
    this.file = file
    var nameEl = $('.file-name', this.dropzone || this.form)
    if(nameEl){ nameEl.textContent = file ? file.name : '' }
  }

  Uploader.prototype._toggleLoading = function(show){
    if(!this.overlay) return
    this.overlay.classList.toggle('active', !!show)
    this.overlay.setAttribute('aria-hidden', show ? 'false' : 'true')
  }

  Uploader.prototype._setProgress = function(p){
    if(!this.progressBarEl) return
    var v = Math.max(0, Math.min(100, p))
    if(this.progressEl){
      this.progressEl.classList.add('is-animated')
      this.progressEl.setAttribute('aria-hidden','false')
      this.progressEl.setAttribute('aria-valuenow', String(Math.round(v)))
    }
    this.progressBarEl.style.width = v + '%'
  }

  Uploader.prototype.upload = function(){
    var self = this
    if(!this.file){
      if(this.input){this.input.focus()}
      return
    }

    var formData = new FormData(this.form || undefined)
    formData.set(this.fieldName, this.file)

    var xhr = new XMLHttpRequest()
    xhr.open(this.method, this.endpoint, true)

    // прогресс
    xhr.upload.onprogress = function(e){
      if(e.lengthComputable){
        var percent = (e.loaded / e.total) * 100
        self._setProgress(percent)
      }
    }

    xhr.onloadstart = function(){
      self._setProgress(0)
      self._toggleLoading(true)
      if(self.submitBtn) self.submitBtn.disabled = true
    }

    xhr.onloadend = function(){
      self._toggleLoading(false)
      if(self.submitBtn) self.submitBtn.disabled = false
      if(self.progressEl){
        self.progressEl.classList.remove('is-animated')
        self.progressEl.setAttribute('aria-hidden','true')
        self.progressEl.setAttribute('aria-valuenow','0')
      }
    }

    xhr.onreadystatechange = function(){
      if(xhr.readyState === 4){
        if(xhr.status >= 200 && xhr.status < 300){
          self._setProgress(100)
          try{
            var res = JSON.parse(xhr.responseText)
            self.onComplete(res)
          }catch(err){
            self.onComplete(xhr.responseText)
          }
        }else{
          self.onError(xhr)
        }
      }
    }

    xhr.onerror = function(){ self.onError(xhr) }

    xhr.send(formData)
  }

  // экспорт
  window.Uploader = Uploader
})()

