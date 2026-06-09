{{- define "lab.labels" -}}
app.kubernetes.io/part-of: agentathon
app.kubernetes.io/managed-by: {{ .Release.Service }}
agentathon/usecase: {{ .Values.usecase | quote }}
{{- end -}}
