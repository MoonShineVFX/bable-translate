dockerid=$(sudo docker ps -q --filter ancestor=babel )
sudo docker build -t babel .
#echo $dockerid
sudo docker stop $dockerid
sudo docker run  -d  -p 5006:5000  --restart always -e "TZ=Asia/Taipei" babel
