require 'json'

system "rm -rf config/autobuy_configs_generated"
system "mkdir config/autobuy_configs_generated"  
Dir["config/autobuy_configs/*"].each do |config_path|
  json = JSON.parse(File.read(config_path))
  asin_list_1 = json["asin_list_1"]
  json["asin_list_1"] = []
  asin_lists = asin_list_1.each_slice(6).to_a

  asin_lists.each_with_index do |sub_asin_list, i|
    sub_json = json.dup
    sub_json["asin_list_1"] = sub_asin_list
    File.write(config_path.gsub("autobuy_configs/", "autobuy_configs_generated/") + "-#{i}", sub_json.to_s)
  end
end
