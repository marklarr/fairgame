require 'json'

system "rm -rf config/autobuy_configs_generated"
system "mkdir config/autobuy_configs_generated"  

Dir["config/autobuy_configs/*"].each_with_index do |config_path, i|
  json = JSON.parse(File.read(config_path))
  asin_list_1 = json["asin_list_1"]
  json["asin_list_1"] = []

  chunk_size = ARGV[i].to_i
  puts "splitting #{config_path} into chunks of #{chunk_size}"
  asin_lists = asin_list_1.each_slice(chunk_size).to_a

  asin_lists.each_with_index do |sub_asin_list, i|
    sub_json = json.dup
    sub_json["asin_list_1"] = sub_asin_list
    File.write(config_path.gsub("autobuy_configs/", "autobuy_configs_generated/") + "-#{i}", sub_json.to_json)
  end
end
