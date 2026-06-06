Flujo de trabajo con Git y estrategia de branching
Para el control de versiones de UTBookLM se utiliza la estrategia de branching GitFlow, ya que se adapta bien proyecto académicos desarrollados por módulos y tiene entregas parciales a lo largo del cuatrimestre. GitFlow define dos ramas principales:

main: contiene únicamente versiones estables del sistema, listas para ser entregadas o desplegadas.
develop: funciona como rama de integración continua; aquí se van uniendo todas las funcionalidades nuevas antes de preparar una release.
A partir de develop se crean ramas de trabajo específicas:

feature/*: ramas de funcionalidad, por ejemplo feature/auth, feature/documents-upload, feature/rag-chat. Cada feature se implementa y prueba de forma aislada y, cuando está lista, se integra nuevamente en develop mediante un pull request.
release/*: ramas de preparación de versión, por ejemplo release/0.1.0. Se crean cuando se quiere congelar una versión para pruebas finales y correcciones menores. Al finalizar, se fusionan en main (creando un tag de versión) y en develop para mantener ambas ramas sincronizadas.
hotfix/*: ramas de corrección urgente sobre producción, por ejemplo hotfix/fix-rag-crash. Nacen desde main cuando se detecta un bug crítico en una versión ya liberada, y después del arreglo se fusionan tanto en main como en develop.
Resumen de reglas de branching
No se trabaja directamente en main.
Toda nueva funcionalidad se implementa en una rama feature/* creada desde develop.
Cuando varias features están listas para una entrega, se crea una rama release/* desde develop para estabilizar la versión.
Si aparece un bug crítico en producción, se crea una rama hotfix/* desde main y, una vez corregido, los cambios se integran tanto en main como en develop.