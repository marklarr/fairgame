jobs = Dir["config/autobuy_configs_generated/*"].map do |config_path|
  fork do
    exec "/home/marklarr/.local/bin/pipenv run python app.py amazon --autobuy-config-path /home/marklarr/github/fairgame/#{config_path} --single-shot --headless &> logs/per_process/#{config_path.split("/").last}.log"
  end
  sleep 1
end

