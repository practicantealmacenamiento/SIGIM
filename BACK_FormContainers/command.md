docker-compose down #Bajamos el servidor
docker-compose build --no-cache #Creamos el contenedor
docker-compose up -d #Subimos el contenedor

docker exec -it django /bin/sh #Entrar en la consola del contenedor y ejecutar comandos
